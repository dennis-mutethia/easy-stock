from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.entities import Product
from utils.inventory.products_categories import ProductsCategories
from utils.stock.stock_take import StockTake

class Products():
    def __init__(self, db): 
        self.db = db
    
    def fetch(self, search, category_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, purchase_price, selling_price, category_id
            FROM products
            WHERE shop_id = %s
            """
            params = [current_user.shop.id]

            if search:
                query += " AND name LIKE %s"
                params.append(f"%{search.upper()}%")
            if int(category_id) > 0:
                query += " AND category_id = %s"
                params.append(category_id)
            
            query = query + " ORDER BY category_id, name"
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            products = []
            for product in data:
                products.append(Product(product[0], product[1], product[2], product[3], product[4]))

            return products

    def add(self, name, purchase_price, selling_price, category_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO products(name, purchase_price, selling_price, category_id, shop_id, created_at, created_by) 
            VALUES(%s, %s, %s, %s, %s, NOW(), %s) 
            ON CONFLICT (name, shop_id) DO NOTHING
            RETURNING id
            """
            params = [name.upper(), purchase_price, selling_price, category_id, current_user.shop.id, current_user.id]
            
            try:
                cursor.execute(query, tuple(params))
                self.db.conn.commit()
                id = cursor.fetchone()[0]
                return id
            except Exception as e:
                self.db.conn.rollback()
                print(f"Error loading stock: {e}")
                return None
                
    def add_stock(self, product_id, name, category_id, purchase_price, selling_price,  in_stock):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO stock (stock_date, product_id, name, category_id, purchase_price, selling_price, opening, additions, shop_id, created_at, created_by)               
            VALUES(CURRENT_DATE, %s, %s, %s, %s, %s, %s, 0, %s, NOW(), %s) 
            ON CONFLICT (stock_date, product_id, shop_id) DO NOTHING
            RETURNING id
            """
            params = [product_id, name.upper(), category_id, purchase_price, selling_price, in_stock, current_user.shop.id, current_user.id]
            
            try:
                cursor.execute(query, tuple(params))
                self.db.conn.commit()
                id = cursor.fetchone()[0]
                return id
            except Exception as e:
                self.db.conn.rollback()
                print(f"Error loading stock: {e}")
                return None
            
    def update(self, id, name, category_id, purchase_price, selling_price):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE products
            SET name=%s, category_id=%s, purchase_price=%s, selling_price=%s, updated_at=NOW(), updated_by=%s
            WHERE id=%s
            """
            params = [name.upper(), category_id, purchase_price, selling_price, current_user.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
    
    def update_stock(self, id, name, category_id, purchase_price, selling_price, in_stock):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE stock
            SET name=%s, category_id=%s, purchase_price=%s, selling_price=%s, opening=%s-additions, updated_at=NOW(), updated_by=%s
            WHERE id=%s
            RETURNING product_id
            """
            params = [name.upper(), category_id, purchase_price, selling_price, in_stock, current_user.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
            product_id = cursor.fetchone()[0]
            return product_id
            
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM products
            WHERE id=%s
            """
            cursor.execute(query, (id,))
            self.db.conn.commit()
        
    def __call__(self):
        search = ''
        category_id = 0     
        current_date = datetime.now().strftime('%Y-%m-%d')
           
        if request.method == 'GET':   
            try:    
                search = request.args.get('search', '')
                category_id = int(request.args.get('category_id', 0))
            except ValueError as e:
                print(f"Error converting category_id: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
        
        if request.method == 'POST':       
            if request.form['action'] == 'add':
                name = request.form['name']   
                category_id_new = request.form['category_id_new']     
                purchase_price = request.form['purchase_price']
                selling_price = request.form['selling_price']   
                in_stock = request.form['in_stock'] 
                product_id = self.add(name, purchase_price, selling_price, category_id_new)
                self.add_stock(product_id, name, category_id_new, purchase_price, selling_price,  in_stock)
            
            elif request.form['action'] == 'update':
                id = request.form['id']
                category_id_new = request.form['category_id']
                name = request.form['name']    
                purchase_price = request.form['purchase_price']
                selling_price = request.form['selling_price']
                in_stock = request.form['in_stock']
                product_id = self.update_stock(id, name, category_id_new, purchase_price, selling_price, in_stock) 
                self.update(product_id, name, category_id_new, purchase_price, selling_price)
                return 'success'
                
            elif request.form['action'] == 'delete':
                id = request.form['item_id']
                self.delete(id) 
                StockTake(self.db).delete(id) 
        
        product_categories = ProductsCategories(self.db).fetch()
        products = StockTake(self.db).fetch(current_date, search, category_id)
        return render_template('inventory/products.html', helper=Helper(), 
                               product_categories=product_categories, products=products, 
                               page_title='Product Categories', search=search, category_id=category_id)
