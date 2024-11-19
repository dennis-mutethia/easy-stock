from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.entities import ProductCategory

class ProductsCategories():
    def __init__(self, db): 
        self.db = db
    
    def fetch(self):
        self.db.ensure_connection() 
        with self.db.conn.cursor() as cursor:
            query = """
            WITH p AS(
                SELECT shop_id, category_id, COUNT(*) counts FROM products GROUP BY shop_id, category_id
            )
            SELECT id, name, COALESCE(counts, 0)
            FROM product_categories 
            LEFT JOIN p ON p.category_id = product_categories.id AND p.shop_id = product_categories.shop_id
            WHERE product_categories.shop_id = %s
            ORDER BY name
            """
            cursor.execute(query, (current_user.shop.id,))
            data = cursor.fetchall()
            product_categories = []
            for shop_type in data:
                product_categories.append(ProductCategory(shop_type[0], shop_type[1], shop_type[2]))
                
            return product_categories 
    
    def add(self, name):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO product_categories(name, shop_id, created_at, created_by) 
            VALUES(%s, %s, NOW(), %s) 
            ON CONFLICT (name, shop_id) DO NOTHING
            RETURNING id
            """
            cursor.execute(query, (name.upper(), current_user.shop.id, current_user.id))
            self.db.conn.commit()
            id = cursor.fetchone()[0]
            return id   
            
    def update(self, id, name):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE product_categories
            SET name=%s, updated_at=NOW(), updated_by=%s
            WHERE id=%s
            """
            params = [name.upper(), current_user.shop.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
            
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM product_categories
            WHERE id=%s
            """
            cursor.execute(query, (id,))
            self.db.conn.commit()
            
    def __call__(self):        
        if request.method == 'POST':       
            if request.form['action'] == 'add':
                name = request.form['name']
                self.add(name)   
                
            elif request.form['action'] == 'update':
                id = request.form['id']
                name = request.form['name']    
                self.update(id, name)
                return 'success'
                   
            elif request.form['action'] == 'delete':
                id = request.form['item_id']
                self.delete(id) 
        
        product_categories = self.fetch()
        return render_template('inventory/products-categories.html', helper=Helper(), 
                               product_categories=product_categories, page_title='Product Categories')
