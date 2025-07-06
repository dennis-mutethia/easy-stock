import pytz, random, math
from datetime import datetime

from utils.db import Db
from utils.entities import Stock

class DemoSTock():
    def __init__(self): 
        self.db = Db()

    def fetch(self, stock_date, shop_id):
        self.db.ensure_connection()
    
        query = """      
        WITH products AS (
            SELECT id, name, category_id
            FROM products 
            WHERE shop_id = %s
        ),
        all_stock AS(
            SELECT id, stock_date, product_id, opening, additions, selling_price, purchase_price
            FROM stock 
            WHERE shop_id = %s
        ),  
        yesterday AS (
            SELECT product_id, opening, additions
            FROM all_stock
            WHERE DATE(stock_date) = DATE(%s) - 1
        ), 
        today AS(
            SELECT id, product_id, COALESCE(opening, 0) AS opening, COALESCE(additions,0) AS additions, selling_price, purchase_price
            FROM all_stock
            WHERE DATE(stock_date) = DATE(%s)
        )
        SELECT today.id, today.product_id, products.name, product_categories.name, COALESCE(yesterday.opening,0), COALESCE(yesterday.additions,0),
            today.opening, today.additions, today.selling_price, today.purchase_price
        FROM today
        INNER JOIN products ON products.id = today.product_id
        INNER JOIN product_categories ON product_categories.id = products.category_id
        LEFT JOIN yesterday ON yesterday.product_id = today.product_id   
        ORDER BY products.category_id, products.name
        """
        params = [shop_id, shop_id, stock_date, stock_date]
                    
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
        shop_ids = [-1]
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        stock_date = current_date 
        for shop_id in shop_ids:  
            self.update(stock_date, shop_id)

DemoSTock()()