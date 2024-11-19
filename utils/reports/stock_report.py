from datetime import datetime
from flask import render_template, request, send_file
from io import BytesIO
from flask_login import current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils.entities import Sale
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories
from utils.stock.stock_take import StockTake

class Stock():
    def __init__(self, stock_date, name, category_name, opening, additions, sold, selling_price):
        self.stock_date = stock_date
        self.name = name
        self.category_name = category_name
        self.opening = opening
        self.additions = additions
        self.sold = sold
        self.selling_price = selling_price
        
class StockReport():
    def __init__(self, db): 
        self.db = db

    def generate_pdf_file(self, stocks, from_date, to_date):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # Set up initial coordinates and fonts
        width, height = letter
        x_margin = 20
        y_margin = 750
        line_height = 20
        col_widths = [50, 150, 100, 50, 50, 50, 50, 50, 50, 0]  # Column widths matching the number of headers

        p.setFont("Helvetica-Bold", 10)
        p.drawString(150, y_margin+10, f"Stock Report From {from_date} to {to_date}")
        p.setFont("Helvetica", 8)

        # Table headers
        y_position = y_margin - line_height
        headers = ["DATE", "PRODUCT NAME", "CATEGORY", "OPENING", "PURCHASES", "CLOSING", "SOLD", "PRICE", "TOTAL", ""]
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
        for stock in stocks:
            closing = stock.opening + stock.additions - stock.sold
            total = stock.selling_price * stock.sold
            if y_position < 50:  # Create a new page if necessary
                p.showPage()
                p.setFont("Helvetica", 8)
                y_position = y_margin
            
            current_x = x_margin
            sale_details = [
                str(stock.stock_date),
                str(stock.name),
                str(stock.category_name),
                str(stock.opening),
                str(stock.additions),
                str(closing),
                str(stock.sold),
                str(stock.selling_price),
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
            WITH sales AS(
                SELECT stock_id, SUM(qty) sold
                FROM bill_entries
                WHERE shop_id = %s AND bill_id>0
                GROUP BY stock_id
            )
            SELECT stock_date, stock.name, product_categories.name AS category_name, stock.opening, stock.additions, COALESCE(sales.sold, 0) AS sold, stock.selling_price
            FROM stock 
            LEFT JOIN sales ON sales.stock_id = stock.id
            LEFT JOIN product_categories ON product_categories.id= stock.category_id
            WHERE (DATE(stock.created_at) BETWEEN DATE(%s) AND DATE(%s)) AND stock.shop_id = %s
            """
            params = [current_user.shop.id, from_date, to_date, current_user.shop.id]
            
            if category_id > 0:
                query = query + " AND stock.category_id = %s "
                params.append(category_id)
            
            query = query + """
            ORDER BY stock_date DESC, category_name, name
            """
            
            if page>0:
                query = query + """
                LIMIT 50 OFFSET %s
                """
                params.append((page - 1)*50)
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            stocks = []
            for datum in data:                    
                stocks.append(Stock(datum[0], datum[1], datum[2], datum[3], datum[4], datum[5], datum[6]))

            return stocks 
         
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = to_date = current_date
        category_id = 0
        page = 1
        download = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                category_id = int(request.args.get('category_id', 0))
                page = int(request.args.get('page', 1))
                download = int(request.args.get('download', download))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        stocks = self.fetch(from_date, to_date, category_id, page) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(stocks)==50 else 0
        grand_total =  0
        for stock in stocks:
            total = stock.selling_price * stock.sold
            grand_total = grand_total + total
        
        if download == 1:   
            pdf_file = self.generate_pdf_file(stocks, from_date, to_date)
            return send_file(pdf_file, as_attachment=True, download_name=f"Stock_Report_from_{from_date}_to_{to_date}_{page} - {current_user.shop.name}.pdf")
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/stock-report.html', page_title='Reports > Stock', helper=Helper(),
                               stocks=stocks, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               current_date=current_date, from_date=from_date, to_date=to_date,
                                page=page, prev_page=prev_page, next_page=next_page)