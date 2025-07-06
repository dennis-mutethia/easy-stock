from flask_login import current_user
import pytz
from datetime import datetime

from utils.db import Db

class DailyStockLoader():
    def __init__(self): 
        self.db = Db()
                    
    def load(self, stock_date, register=False):
        self.db.create_current_month_partition()
        
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:     
            query = """         
            WITH products AS (
                SELECT id, shop_id, name, category_id, purchase_price, selling_price
                FROM products 
            ),
            yesterday AS (
                SELECT product_id, purchase_price, selling_price, opening, additions
                FROM stock
                WHERE DATE(stock_date) = DATE(%s) - 1
            ),
            today AS (
                SELECT 
                    DATE(%s) AS stock_date, 
                    COALESCE(yesterday.product_id, products.id) AS product_id, 
                    COALESCE(yesterday.purchase_price, products.purchase_price) AS purchase_price,
                    COALESCE(yesterday.selling_price, products.selling_price) AS selling_price,
                    COALESCE((yesterday.opening+yesterday.additions), 0) AS opening,
                    0 AS additions,
                    products.shop_id AS shop_id, 
                    CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' AS created_at, 
                    0 AS created_by              
                FROM products
                LEFT JOIN yesterday ON yesterday.product_id = products.id
            )
            INSERT INTO stock (stock_date, product_id, purchase_price, selling_price, opening, additions, shop_id, created_at, created_by) 
            SELECT * FROM today            
            """
            
            params = [stock_date, stock_date]
            if register:
                query += """
                WHERE shop_id = %s
                """
                params.append(current_user.shop.id)
            
            query += """  
            ON CONFLICT (stock_date, product_id, shop_id) DO NOTHING
            """          
     
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
    
    def __call__(self):
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        stock_date = current_date 
        self.load(stock_date)

DailyStockLoader()()