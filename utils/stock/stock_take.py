import pytz
from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Stock
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

class StockTake():
    def __init__(self, db): 
        self.db = db
                    
    def load(self, stock_date):
        self.db.create_current_month_partition()
        
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:     
            query = """         
            WITH products AS (
                SELECT id, name, category_id, purchase_price, selling_price
                FROM products 
                WHERE shop_id = %s
            ),
            yesterday AS (
                SELECT product_id, name, category_id, purchase_price, selling_price, opening, additions
                FROM stock
                WHERE DATE(stock_date) = DATE(%s) - 1
            ),
            today AS (
                SELECT DATE(%s) AS stock_date, 
                    COALESCE(yesterday.product_id, products.id) AS product_id, 
                    COALESCE(yesterday.name, products.name) AS name, 
                    COALESCE(yesterday.category_id, products.category_id) AS category_id,
                    COALESCE(yesterday.purchase_price, products.purchase_price) AS purchase_price,
                    COALESCE(yesterday.selling_price, products.selling_price) AS selling_price,
                    COALESCE((yesterday.opening+yesterday.additions), 0) AS opening,
                    0 AS additions,
                    %s AS shop_id, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' AS created_at, %s AS created_by              
                FROM products
                LEFT JOIN yesterday ON yesterday.product_id = products.id
            )
            INSERT INTO stock (stock_date, product_id, name, category_id, purchase_price, selling_price, opening, additions, shop_id, created_at, created_by) 
            SELECT * FROM today
            ON CONFLICT (stock_date, product_id, shop_id) DO NOTHING
            """
            params = [current_user.shop.id, stock_date, stock_date, current_user.shop.id, current_user.id]
     
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
    
    def fetch(self, stock_date, search, category_id, in_stock=0):
        self.db.ensure_connection()
    
        query = """
        WITH all_stock AS(
            SELECT id, stock_date, product_id, name, category_id, opening, additions, selling_price, purchase_price
            FROM stock 
            WHERE shop_id = %s
        ),  
        yesterday AS (
            SELECT product_id, opening, additions
            FROM all_stock
            WHERE DATE(stock_date) = DATE(%s) - 1
        ), 
        today AS(
            SELECT id, product_id, name, category_id, COALESCE(opening, 0) AS opening, COALESCE(additions,0) AS additions, selling_price, purchase_price
            FROM all_stock
            WHERE DATE(stock_date) = DATE(%s)
        )
        SELECT today.id, today.product_id, today.name, product_categories.name, COALESCE(yesterday.opening,0), COALESCE(yesterday.additions,0),
            today.opening, today.additions, today.selling_price, today.purchase_price
        FROM today
        INNER JOIN product_categories ON product_categories.id = today.category_id
        LEFT JOIN yesterday ON yesterday.product_id = today.product_id            
        WHERE (today.opening + today.additions) >= %s        
        """
        params = [current_user.shop.id, stock_date, stock_date, in_stock]

        if search:
            query += " AND today.name LIKE %s"
            params.append(f"%{search.upper()}%")
        if int(category_id) > 0:
            query += " AND today.category_id = %s"
            params.append(category_id)
        
        query = query + """
            ORDER BY today.category_id, today.name
            """
            
        with self.db.conn.cursor() as cursor:    
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            stocks = []
            for stock in data:
                stocks.append(Stock(stock[0], stock[1], stock[2], stock[3], stock[4], stock[5], stock[6], stock[7], stock[8], stock[9]))

            return stocks
        
    def get_total(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH all_stock AS(
                SELECT (COALESCE(opening, 0) + COALESCE(additions, 0)) AS in_stock, purchase_price, selling_price
                FROM stock 
                WHERE stock_date=%s AND shop_id = %s AND purchase_price != 'Nan' AND selling_price != 'Nan'
            )        
        
            SELECT SUM(in_stock * purchase_price) capital, SUM(in_stock * selling_price) AS stock_amount 
            FROM all_stock
            WHERE in_stock != 'Nan'
            """
            params = [report_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchone()
            if data:
                return int(data[0]) if data[0] is not None else 0, int(data[1]) if data[1] is not None else 0
            else:
                return None
            
    def update(self, id, opening, additions):
        self.db.ensure_connection()
        
        query = """
        UPDATE stock
        SET opening=%s, additions=%s, updated_at=CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', updated_by=%s
        WHERE id=%s
        """
        params = [opening, additions, current_user.id, id]
        
        with self.db.conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
            
    def delete(self, product_id):
        self.db.ensure_connection()
        
        query = """
        DELETE FROM stock
        WHERE product_id=%s AND stock_date=DATE(CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi')
        """
            
        with self.db.conn.cursor() as cursor:
            cursor.execute(query, (product_id,))
            self.db.conn.commit()
             
    def __call__(self):
        search = ''
        category_id = 0   
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        stock_date = current_date   
        self.load(stock_date)
        
        if request.method == 'GET':   
            try:    
                search = request.args.get('search', '')
                category_id = int(request.args.get('category_id', 0))
                stock_date = request.args.get('stock_date', default=current_date)
            except ValueError as e:
                print(f"Error converting category_id: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
        
        if request.method == 'POST':       
            if request.form['action'] == 'update':
                id = request.form['id']
                opening = request.form['opening']
                additions = request.form['additions']     
                self.update(id, opening, additions)
                return 'success'             
             
        product_categories = ProductsCategories(self.db).fetch()
        stocks = self.fetch(stock_date, search, category_id)
        return render_template('stock/stock-take.html', helper=Helper(), menu='stock', sub_menu='stock_take',
                               product_categories=product_categories, stocks=stocks, 
                               page_title='Stock Take', stock_date=stock_date, current_date=current_date, search=search, category_id=category_id)
