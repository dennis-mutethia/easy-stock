from datetime import datetime
from flask import render_template, request, send_file
from io import BytesIO
from flask_login import current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils.entities import Statement
from utils.helper import Helper

class StatementOfAccount():
    def __init__(self, db): 
        self.db = db

    def generate_pdf_file(self, sales, from_date, to_date):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # Set up initial coordinates and fonts
        width, height = letter
        x_margin = 20
        y_margin = 750
        line_height = 20
        col_widths = [150, 100, 100, 50, 50, 0]  # Column widths matching the number of headers

        p.setFont("Helvetica-Bold", 10)
        p.drawString(150, y_margin+10, f"Sales Report From {from_date} to {to_date}")
        p.setFont("Helvetica", 8)

        # Table headers
        y_position = y_margin - line_height
        headers = ["PRODUCT NAME", "CATEGORY NAME", "PRICE", "SOLD", "TOTAL", ""]
        current_x = x_margin

        # Draw headers and top border
        for i, header in enumerate(headers):
            p.drawString(current_x + 5, y_position, header)  # Slightly offset text from the border
            current_x += col_widths[i]

        # Draw borders for header row
        p.line(x_margin, y_position + line_height, width - x_margin, y_position + line_height)  # Top border
        p.line(x_margin, y_position, width - x_margin, y_position)  # Bottom border

        current_x = x_margin
        for col_width in col_widths:
            p.line(current_x, y_position + line_height, current_x, y_position)  # Vertical borders
            current_x += col_width

        y_position -= line_height

        # Iterate over the bills and add each bill's details
        for sale in sales:
            total = sale.selling_price * sale.sold
            if y_position < 50:  # Create a new page if necessary
                p.showPage()
                p.setFont("Helvetica", 8)
                y_position = y_margin
            
            current_x = x_margin
            sale_details = [
                str(sale.item_name),
                str(sale.category_name),
                str(sale.selling_price),
                str(sale.sold),
                str(total),
                ''
            ]

            # Draw the bill details and borders
            for i, detail in enumerate(sale_details):
                p.drawString(current_x + 5, y_position, detail)
                current_x += col_widths[i]
            
            # Draw borders for each row
            p.line(x_margin, y_position + line_height, width - x_margin, y_position + line_height)  # Top border
            p.line(x_margin, y_position, width - x_margin, y_position)  # Bottom border

            current_x = x_margin
            for col_width in col_widths:
                p.line(current_x, y_position + line_height, current_x, y_position)  # Vertical borders
                current_x += col_width

            y_position -= line_height

        # Finish the PDF document
        p.showPage()
        p.save()

        buffer.seek(0)
        return buffer
    
    
            
    def fetch(self, from_date, to_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
                                
            WITH all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    COALESCE(opening, 0) AS opening, 
                    COALESCE(additions, 0) AS additions, 
                    purchase_price,
                    selling_price
                FROM stock
                WHERE shop_id = %s AND DATE(stock_date) BETWEEN DATE(%s) AND DATE(%s)
            ),
            sales AS(
                SELECT 
                    yesterday.stock_date AS date, 
                    yesterday.purchase_price,
                    yesterday.selling_price,
                    (today.opening-(yesterday.opening+yesterday.additions)) AS sold,
                    yesterday.additions
                FROM all_stock AS today
                INNER JOIN all_stock AS yesterday ON yesterday.product_id = today.product_id
                    AND DATE(yesterday.stock_date) = DATE(today.stock_date) - 1
            ),
            totals AS(
                SELECT date, SUM(sold*selling_price) AS total_sales, SUM(additions*purchase_price) AS total_purchases, 0 AS expenses
                FROM sales  
                GROUP BY date
            ),
            expenses AS(
                SELECT date,0,0,SUM(amount)
                FROM expenses
                WHERE shop_id = %s AND date BETWEEN DATE(%s) AND DATE(%s)
                GROUP BY date
            ),
            final AS(
                SELECT * FROM totals
                UNION SELECT * FROM expenses
            )
            SELECT * FROM final 
            ORDER BY date ASC
            """
            params = [
                current_user.shop.id, from_date, to_date,
                current_user.shop.id, from_date, to_date
            ]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            statements = []
            for datum in data:                   
                statements.append(Statement(datum[0], datum[1], datum[2], datum[3]))

            return statements 
         
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        to_date = current_date
        download = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                page = int(request.args.get('page', 1))
                download = int(request.args.get('download', download))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        statements = self.fetch(from_date, to_date) 
                
        if download == 1:   
            pdf_file = self.generate_pdf_file(statements, from_date, to_date)
            return send_file(pdf_file, as_attachment=True, download_name=f"Statement_of_Account_from_{from_date}_to_{to_date}_{page} - {current_user.shop.name}.pdf")
                    
        return render_template('reports/statement-of-account.html', page_title='Reports >Statement of Account', helper=Helper(),
                               statements=statements, from_date=from_date, to_date=to_date, current_date=current_date
                               )