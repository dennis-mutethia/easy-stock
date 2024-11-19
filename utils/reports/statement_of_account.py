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
            WITH sales AS(
                SELECT DATE(created_at) AS date, SUM(total) AS sales,0 AS purchases,0 AS expenses
                FROM bills
                WHERE DATE(created_at) BETWEEN DATE(%s) AND DATE(%s) AND shop_id=%s AND total != 'Nan'
                GROUP BY date
            ),            
            purchases AS(
                SELECT stock_date,0,SUM(additions*purchase_price), 0
                FROM stock
                WHERE stock_date BETWEEN DATE(%s) AND DATE(%s) AND shop_id = %s
                GROUP BY stock_date
            ),
            expenses AS(
                SELECT date,0,0,SUM(amount)
                FROM expenses
                WHERE date BETWEEN DATE(%s) AND DATE(%s) AND shop_id = %s
                GROUP BY date
            ),
            final AS(
                SELECT * FROM sales
                UNION SELECT * FROM purchases
                UNION SELECT * FROM expenses
            )
            SELECT * FROM final 
            ORDER BY date ASC, sales DESC, purchases DESC, expenses DESC
            """
            params = [
                from_date, to_date, current_user.shop.id,
                from_date, to_date, current_user.shop.id,
                from_date, to_date, current_user.shop.id
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