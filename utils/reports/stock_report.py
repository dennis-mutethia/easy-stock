import pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user 

from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

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

    def fetch(self, from_date, category_id=0):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """      
            WITH products AS (
                SELECT id, name, category_id
                FROM products 
                WHERE shop_id = %s
            ),         
            all_stock AS (
                SELECT 
                    stock.stock_date, 
                    stock.product_id, 
                    products.name AS item_name, 
                    products.category_id,
                    pc.name AS category_name, 
                    COALESCE(stock.opening, 0) AS opening, 
                    COALESCE(stock.additions, 0) AS additions, 
                    stock.selling_price
                FROM stock
                INNER JOIN products ON products.id = stock.product_id
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
                    today.stock_date, 
                    today.item_name, 
                    today.category_id,
                    today.category_name,
                    today.selling_price,
                    today.opening,
                    today.additions,
                    (today.opening + today.additions - tomorrow.opening) AS sold
                FROM today
                INNER JOIN tomorrow ON tomorrow.product_id = today.product_id
            ) 
            SELECT 
                stock_date,
                item_name,
                category_name,
                opening,
                additions,
                sold,
                selling_price
            FROM source  
            WHERE sold > 0
            """
            params = [current_user.shop.id, current_user.shop.id, from_date, from_date]
            
            if category_id > 0:
                query = query + " AND category_id = %s "
                params.append(category_id)
            
            query = query + """
            ORDER BY category_name, item_name
            """
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            stocks = []
            for datum in data:                    
                stocks.append(Stock(datum[0], datum[1], datum[2], datum[3], datum[4], datum[5], datum[6]))

            return stocks 
         
    def __call__(self):
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')
        report_date = max_date
        category_id = 0
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', report_date)
                category_id = int(request.args.get('category_id', 0))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        stocks = self.fetch(report_date, category_id) 
        grand_total =  0
        for stock in stocks:
            total = stock.selling_price * stock.sold
            grand_total = grand_total + total
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/stock-report.html', page_title='Reports > Stock', helper=Helper(), menu='reports', sub_menu='stock_report',
                               stocks=stocks, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               max_date=max_date, report_date=report_date)