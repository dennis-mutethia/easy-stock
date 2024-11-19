from datetime import datetime
from flask import render_template, request, send_file
from io import BytesIO
from flask_login import current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils.entities import Purchase
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

class PurchasesReport():
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
        col_widths = [150, 100, 100, 100, 50, 0]  # Column widths matching the number of headers

        p.setFont("Helvetica-Bold", 10)
        p.drawString(150, y_margin+10, f"Purchases Report From {from_date} to {to_date}")
        p.setFont("Helvetica", 8)

        # Table headers
        y_position = y_margin - line_height
        headers = ["PRODUCT NAME", "CATEGORY NAME", "PURCHASE PRICE", "PURCHASES", "TOTAL", ""]
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
            total = sale.purchase_price * sale.additions
            if y_position < 50:  # Create a new page if necessary
                p.showPage()
                p.setFont("Helvetica", 8)
                y_position = y_margin
            
            current_x = x_margin
            sale_details = [
                str(sale.name),
                str(sale.category_name),
                str(sale.purchase_price),
                str(sale.additions),
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
    
    def fetch(self, from_date, to_date, category_id=0, page=0):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT DATE(s.updated_at) AS report_date, s.name, pc.name AS category_name, s.purchase_price, SUM(COALESCE(s.additions,0)) additions 
            FROM stock s
            LEFT JOIN product_categories pc ON pc.id= s.category_id   
            WHERE (DATE(s.updated_at) BETWEEN DATE(%s) AND DATE(%s)) AND s.shop_id = %s AND s.additions IS NOT NULL AND s.additions>0
            """
            params = [from_date, to_date, current_user.shop.id]
            
            if category_id > 0:
                query = query + " AND s.category_id = %s "
                params.append(category_id)
            
            query = query + """
            GROUP BY report_date, s.name, pc.name, s.purchase_price
            ORDER BY report_date ASC, pc.name, s.name
            """
            
            if page>0:
                query = query + """
                LIMIT 50 OFFSET %s
                """
                params.append((page - 1)*50)
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            purchases = []
            for datum in data:                       
                purchases.append(Purchase(datum[0], datum[1], datum[2], datum[3], datum[4]))

            return purchases 
         
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = to_date = current_date
        page = 1
        download = 0
        category_id = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                category_id = int(request.args.get('category_id', 0))
                page = int(request.args.get('page', 1))
                download = int(request.args.get('download', download))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        purchases = self.fetch(from_date, to_date, category_id, page) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(purchases)==50 else 0
        grand_total =  0
        for purchase in purchases:
            total = purchase.purchase_price * purchase.additions
            grand_total = grand_total + total
        
        if download == 1:   
            pdf_file = self.generate_pdf_file(purchases, from_date, to_date)
            return send_file(pdf_file, as_attachment=True, download_name=f"Purchases_Report_from_{from_date}_to_{to_date}_{page} - {current_user.shop.name}.pdf")
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/purchases-report.html', page_title='Reports > Purchases', helper=Helper(),
                               purchases=purchases, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               current_date=current_date, from_date=from_date, to_date=to_date, 
                                page=page, prev_page=prev_page, next_page=next_page)