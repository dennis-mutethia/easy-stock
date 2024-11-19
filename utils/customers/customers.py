from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.entities import Customer

class Customers():
    def __init__(self, db): 
        self.db = db
               
    def fetch_by_id(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, phone
            FROM customers
            WHERE id=%s 
            """
            params = [id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchone()
            if data:
                return Customer(data[0], data[1], data[2])
            else:
                return None    
    
    def fetch(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            #$id, $name, $selling_price, remaining, $temp_qty
            query = """
            SELECT id, name, phone
            FROM customers
            WHERE shop_id=%s 
            ORDER BY name
            """
            params = [current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            customers = []
            for datum in data:
                customers.append(Customer(datum[0], datum[1], datum[2]))

            return customers
    
    def add(self, name, phone):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO customers(name, phone, shop_id, created_at, created_by) 
            VALUES(%s, %s, %s, NOW(), %s) 
            ON CONFLICT (phone, shop_id) DO NOTHING
            RETURNING id
            """
            cursor.execute(query, (name.upper(), phone, current_user.shop.id, current_user.id))
            self.db.conn.commit()
            id = cursor.fetchone()[0]
            return id   
            
    def update(self, id, name, phone):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE customers
            SET name=%s, phone=%s, updated_at=NOW(), updated_by=%s
            WHERE id=%s
            """
            params = [name.upper(), phone, current_user.shop.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
            
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM customers
            WHERE id=%s
            """
            cursor.execute(query, (id,))
            self.db.conn.commit()
        
            
    def __call__(self):        
        if request.method == 'POST':       
            if request.form['action'] == 'add':
                name = request.form['name']
                phone = request.form['phone']
                self.add(name, phone)   
                
            elif request.form['action'] == 'update':
                id = request.form['id']
                name = request.form['name']
                phone = request.form['phone'] 
                self.update(id, name, phone)
                return 'success'
                   
            elif request.form['action'] == 'delete':
                id = request.form['customer_id']
                self.delete(id) 
        
        customers = self.fetch()
        return render_template('customers/index.html', helper=Helper(), 
                               customers=customers, page_title='Customers')
