from datetime import datetime
from flask import render_template, request
from flask_login import current_user
import pytz

from utils.entities import Stock
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

class StockTake():
    def __init__(self, db): 
        self.db = db
   
    def fetch(self, stock_date, search, category_id, in_stock=0):
        self.db.ensure_connection()
        shop_id = current_user.shop.id
    
        query = """       
        WITH products AS (
            SELECT id, name, category_id
            FROM products  
            WHERE shop_id = %s
        ),
        all_stock AS (
            SELECT 
                id, 
                stock_date, 
                product_id, 
                CASE WHEN opening   = 'Nan' THEN 0 ELSE opening   END AS opening,
                CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions, 
                selling_price, 
                purchase_price
            FROM stock 
            WHERE shop_id = %s
        ),  
        max_date AS (
            SELECT MAX(stock_date) AS md
            FROM stock 
            WHERE shop_id = %s AND DATE(stock_date) < DATE(%s)
        ),
        yesterday AS (
            SELECT 
                product_id,
                CASE WHEN opening   = 'Nan' THEN 0 ELSE opening   END AS opening,
                CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions 
            FROM stock
            INNER JOIN max_date ON max_date.md = DATE(stock.stock_date)
        ),
        today AS (
            SELECT 
                all_stock.id, 
                product_id, 
                name, 
                category_id, 
                opening,
                additions,
                selling_price, 
                purchase_price
            FROM all_stock
            JOIN products ON products.id = all_stock.product_id
            WHERE DATE(stock_date) = DATE(%s)
        )
        SELECT 
            today.id, today.product_id, today.name, product_categories.name,
            COALESCE(yesterday.opening, 0)   AS yesterday_opening,
            COALESCE(yesterday.additions, 0) AS yesterday_additions,
            today.opening, today.additions,
            today.selling_price, today.purchase_price
        FROM today
        INNER JOIN product_categories ON product_categories.id = today.category_id
        LEFT JOIN yesterday ON yesterday.product_id = today.product_id
        WHERE (today.opening + today.additions) >= %s
        """
        params = [shop_id, shop_id, shop_id, stock_date, stock_date, in_stock]

        if search:
            query += " AND today.name LIKE %s"
            params.append(f"%{search.upper()}%")
        if int(category_id) > 0:
            query += " AND today.category_id = %s"
            params.append(category_id)
        
        query += " ORDER BY today.category_id, today.name"
            
        with self.db.conn.cursor() as cursor:    
            cursor.execute(query, tuple(params))
            return [Stock(*row) for row in cursor.fetchall()]
        
    def get_total(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                WITH all_stock AS (
                    SELECT (COALESCE(opening, 0) + COALESCE(additions, 0)) AS in_stock,
                           purchase_price, selling_price
                    FROM stock 
                    WHERE stock_date = %s AND shop_id = %s
                      AND purchase_price != 'Nan' AND selling_price != 'Nan'
                )
                SELECT COALESCE(SUM(in_stock * purchase_price), 0) AS capital,
                       COALESCE(SUM(in_stock * selling_price),  0) AS stock_amount
                FROM all_stock
                WHERE in_stock != 'Nan'
                """,
                (report_date, current_user.shop.id)
            )
            row = cursor.fetchone()
            # Always return a tuple — callers expect (capital, stock_amount)
            return (int(row[0]), int(row[1])) if row else (0, 0)
            
    def update(self, id, opening, additions):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE stock
                    SET opening = %s, additions = %s,
                        updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                        updated_by = %s
                    WHERE id = %s
                    """,
                    (opening, additions, current_user.id, id)
                )
                self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise
            
    def delete(self, product_id):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM stock
                    WHERE product_id = %s
                      AND stock_date = DATE(CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi')
                    """,
                    (product_id,)
                )
                self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise
    
    def add(self, name, purchase_price, selling_price, category_id):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO products(name, purchase_price, selling_price, category_id, shop_id, created_at, created_by) 
                    VALUES(%s, %s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
                    ON CONFLICT (name, shop_id) DO UPDATE
                        SET purchase_price = EXCLUDED.purchase_price,
                            selling_price  = EXCLUDED.selling_price,
                            updated_at     = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                            updated_by     = EXCLUDED.created_by
                    RETURNING id
                    """,
                    (name.upper(), purchase_price, selling_price, category_id, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            self.db.conn.rollback()
            print(f"Error adding product: {e}")
            return None
                
    def add_stock(self, product_id, purchase_price, selling_price, in_stock):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO stock(stock_date, product_id, purchase_price, selling_price, opening, additions, shop_id, created_at, created_by)               
                    VALUES(CURRENT_DATE, %s, %s, %s, %s, 0, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
                    ON CONFLICT (stock_date, product_id, shop_id) DO UPDATE
                        SET purchase_price = EXCLUDED.purchase_price,
                            selling_price  = EXCLUDED.selling_price,
                            opening        = EXCLUDED.opening,
                            updated_at     = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                            updated_by     = EXCLUDED.created_by
                    RETURNING id
                    """,
                    (product_id, purchase_price, selling_price, in_stock, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            self.db.conn.rollback()
            print(f"Error adding stock: {e}")
            return None
             
    def __call__(self):
        nairobi = pytz.timezone("Africa/Nairobi")
        current_date = datetime.now(nairobi).strftime('%Y-%m-%d')
        stock_date   = current_date
        search       = ''
        category_id  = 0

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                product_id = self.add(
                    request.form['name'],
                    request.form['purchase_price'],
                    request.form['selling_price'],
                    request.form['category_id_new']
                )
                if product_id:
                    self.add_stock(
                        product_id,
                        request.form['purchase_price'],
                        request.form['selling_price'],
                        request.form['in_stock']
                    )
            elif action == 'update':
                self.update(request.form['id'], request.form['opening'], request.form['additions'])
                return 'success'

        elif request.method == 'GET':
            try:
                search      = request.args.get('search', '')
                category_id = int(request.args.get('category_id', 0))
                stock_date  = request.args.get('stock_date', current_date)
            except ValueError as e:
                print(f"Error parsing query params: {e}")

        return render_template(
            'stock/stock-take.html',
            helper=Helper(),
            menu='stock',
            sub_menu='stock_take',
            product_categories=ProductsCategories(self.db).fetch(),
            stocks=self.fetch(stock_date, search, category_id),
            page_title='Stock Take',
            stock_date=stock_date,
            current_date=current_date,
            search=search,
            category_id=category_id
        )