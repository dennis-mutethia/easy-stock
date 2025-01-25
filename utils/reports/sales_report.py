import pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.entities import Sale
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

class SalesReport():
    def __init__(self, db): 
        self.db = db

    def fetch(self, report_date, category_id=0):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """            
            WITH all_stock AS (
                SELECT 
                    stock.stock_date, 
                    stock.product_id, 
                    stock.name AS item_name, 
                    stock.category_id,
                    pc.name AS category_name, 
                    COALESCE(stock.opening, 0) AS opening, 
                    COALESCE(stock.additions, 0) AS additions, 
                    stock.selling_price
                FROM stock
                LEFT JOIN product_categories pc ON pc.id= stock.category_id   
                WHERE stock.shop_id = %s
            ),
            today AS (
                SELECT *
                FROM all_stock
                WHERE DATE(stock_date) = DATE(%s)
            ),
            tomorrow AS (
                SELECT *
                FROM all_stock
                WHERE DATE(stock_date) = DATE(%s) + 1
            ),
            source AS(
                SELECT 
                    today.stock_date AS report_date, 
                    today.item_name, 
                    today.category_id,
                    today.category_name,
                    today.selling_price,
                    (today.opening + today.additions - tomorrow.opening) AS sold
                FROM today
                INNER JOIN tomorrow ON tomorrow.product_id = today.product_id
            ) 
            SELECT 
                report_date,
                item_name,
                category_name,
                selling_price,
                sold
            FROM source   
            WHERE sold > 0     
            """
            params = [current_user.shop.id, report_date, report_date]
            
            if category_id > 0:
                query = query + " AND category_id = %s "
                params.append(category_id)
            
            query = query + """
            ORDER BY sold DESC
            """
                        
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            sales = []
            for datum in data:                       
                sales.append(Sale(datum[0], datum[1], datum[2], datum[3], datum[4]))

            return sales 
         
    def __call__(self):
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')
        report_date = max_date
        category_id = 0
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('from_date', report_date)
                category_id = int(request.args.get('category_id', 0))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        sales = self.fetch(report_date, category_id) 
        grand_total =  0
        for sale in sales:
            total = sale.selling_price * sale.sold
            grand_total = grand_total + total
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/sales-report.html', page_title='Reports > Sales', helper=Helper(), menu='reports', sub_menu='sales_report',
                               sales=sales, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               report_date=report_date, max_date=max_date)