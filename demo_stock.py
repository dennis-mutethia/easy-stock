import pytz, random, math
from datetime import datetime

from utils.db import Db
from utils.entities import Stock

class DemoSTock():
    def __init__(self): 
        self.db = Db()
                    
    def load(self, stock_date, shop_id):
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
            params = [shop_id, stock_date, stock_date, shop_id, 0]
     
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
    
    def fetch(self, stock_date, shop_id):
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
        """
        params = [shop_id, stock_date, stock_date]
        
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
    
    def update(self, stock_date, shop_id):
        stocks = self.fetch(stock_date, shop_id)
        stocks = random.sample(stocks, min(15, len(stocks)))
        stocks = random.sample(stocks, 15)
        self.db.ensure_connection()
        for stock in stocks:
            opening = stock.yesterday_opening + stock.yesterday_additions
            new_opening = random.randint(math.ceil(opening * 0.7), opening)
            additions = 0            
            #if (new_opening > 5 and new_opening % 5 == 0) or (new_opening > 3 and new_opening % 3 == 0) or new_opening <= 3:
            sold = 5 #opening - new_opening
            additions = random.randint(0, sold)
            opening = new_opening  
            
            #if old_opening != new_opening or additions > 0:
            print(f'Updating {stock.name} opening={opening} additions={additions}')               
                
            query = """
            UPDATE stock
            SET opening=%s, additions=%s, updated_at=CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', updated_by=%s
            WHERE id=%s
            """
            params = [opening, additions, 0, stock.id]
            
            with self.db.conn.cursor() as cursor:                
                cursor.execute(query, tuple(params))
                self.db.conn.commit()           
        
    def __call__(self):
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        stock_date = current_date 
        for shop_id in [1, 2]:  
            self.load(stock_date, shop_id)
            self.update(stock_date, shop_id)

DemoSTock()()