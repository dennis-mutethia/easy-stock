from datetime import datetime
from flask import render_template, request, send_file
from io import BytesIO
from flask_login import current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils.entities import Profit
from utils.helper import Helper
from utils.settings.system_users import SystemUsers

class ProfitReport():
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
            WITH exp AS(
                SELECT date, SUM(amount) total_expenses
                FROM expenses
                GROUP BY date
            ),
            sales AS(
                SELECT DATE(b.created_at) AS report_date, be.price*be.qty AS sales, s.purchase_price*be.qty AS cost
                FROM bills b
                JOIN bill_entries be ON be.bill_id = b.id
                JOIN stock s ON s.id = be.stock_id 
                WHERE DATE(b.created_at) BETWEEN DATE(%s) AND DATE(%s) AND b.shop_id=%s AND total != 'Nan'
            ),
            totals AS(
                SELECT report_date, SUM(sales) AS total_sales, SUM(cost) AS total_cost
                FROM sales  
                GROUP BY report_date
            )
            SELECT report_date, total_sales, total_cost, COALESCE(total_expenses,0) AS total_expenses
            FROM totals
            LEFT JOIN exp ON exp.date=totals.report_date    
            ORDER BY report_date     
            """
            params = [from_date, to_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            profits = []
            for datum in data:                
                profits.append(Profit(datum[0], datum[1], datum[2], datum[3]))

            return profits 
         
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        to_date = current_date
        page = 1
        download = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                page = int(request.args.get('page', 1))
                download = int(request.args.get('download', download))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        profits = self.fetch(from_date, to_date) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(profits)==50 else 0
        
        if download == 1:   
            pdf_file = self.generate_pdf_file(profits, from_date, to_date)
            return send_file(pdf_file, as_attachment=True, download_name=f"Profit_and_Loss_Report_from_{from_date}_to_{to_date}_{page} - {current_user.shop.name}.pdf")
                    
        return render_template('reports/profit-report.html', page_title='Reports > Profit & Loss', helper=Helper(),
                               profits=profits, from_date=from_date, to_date=to_date, current_date=current_date,
                               page=page, prev_page=prev_page, next_page=next_page
                               )