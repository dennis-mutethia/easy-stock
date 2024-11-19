from flask import redirect, render_template, request, url_for
from flask_login import current_user

from utils.entities import Shop, ShopType
from utils.helper import Helper

class MyShops():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no
            FROM shops 
            WHERE company_id = %s 
            """
            params = [current_user.company.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            shops = []
            for datum in data:   
                shop_type = self.fetch_shop_type_by_id(datum[2])   
                shops.append(Shop(datum[0], datum[1], shop_type, datum[3], datum[4], datum[5], datum[6], datum[7], datum[8], datum[9]))

            return shops 
               
    def get_by_id(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no
            FROM shops 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                shop_type = self.fetch_shop_type_by_id(data[2])
                return Shop(data[0], data[1], shop_type, data[3], data[4], data[5], data[6], data[7], data[8], data[9])
            else:
                return None    
    
    def add(self, name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no, created_by):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO shops(name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no, created_at, created_by) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s) 
            RETURNING id
            """
            cursor.execute(query, (name.upper(), shop_type_id, company_id, location.upper(), phone_1, phone_2, paybill, account_no, till_no, created_by))
            self.db.conn.commit()
            shop_id = cursor.fetchone()[0]
            return shop_id
        
    def update(self, shop_id, name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no, updated_by):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE shops 
            SET name = %s, shop_type_id = %s, company_id = %s, location = %s, phone_1 = %s, phone_2 = %s, paybill = %s, account_no = %s, till_no = %s, updated_at=NOW(), updated_by = %s 
            WHERE id = %s          
            """
            cursor.execute(query, (name.upper(), shop_type_id, company_id, location.upper(), phone_1, phone_2, paybill, account_no, till_no, updated_by, shop_id))
            self.db.conn.commit()
            
    def switch(self, shop_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE users
            SET shop_id = %s
            WHERE id = %s
            """
            cursor.execute(query, (shop_id, current_user.id))
            self.db.conn.commit()
            
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM shops
            WHERE id = %s
            """
            cursor.execute(query, (id,))
            self.db.conn.commit()
            
    def fetch_shop_types(self):
        self.db.ensure_connection() 
        with self.db.conn.cursor() as cursor:
            cursor.execute("SELECT id, name, description FROM shop_types ORDER BY name")
            data = cursor.fetchall()
            shop_types = []
            for shop_type in data:
                shop_types.append(ShopType(shop_type[0], shop_type[1], shop_type[2]))
                
            return shop_types 
            
    def fetch_shop_type_by_id(self, id):
        self.db.ensure_connection() 
        with self.db.conn.cursor() as cursor:
            query = "SELECT id, name, description FROM shop_types WHERE id = %s"
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return ShopType(data[0], data[1], data[2])
            else:
                return None     
        
    def __call__(self):   
        toastr_message = None             
        if request.method == 'POST':       
            if request.form['action'] == 'add' or request.form['action'] == 'update':  
                name = request.form['name']
                location = request.form['location']      
                shop_type_id = request.form['shop_type_id']   
                company_id = current_user.company.id  
                phone_1 = request.form['phone_1']       
                phone_2 = request.form['phone_2']       
                paybill = request.form['paybill']       
                account_no = request.form['account_no']       
                till_no = request.form['till_no']    
                created_by = current_user.id 
                if request.form['action'] == 'add':
                    self.add(name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no, created_by)
                    toastr_message = f'{name} Added Successfully'
                else:
                    shop_id = request.form['shop_id']
                    self.update(shop_id, name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no, created_by)
                    toastr_message = f'{name} Updated Successfully'
            
            elif request.form['action'] == 'switch':
                shop_id = request.form['shop_id']
                name = request.form['name']
                self.switch(shop_id)
                toastr_message = f'Successfully Switched Shop to {name}'
                return redirect(url_for('myShops'))
                    
            elif request.form['action'] == 'delete':
                shop_id = request.form['shop_id']
                self.delete(shop_id)
                toastr_message = f'Shop Deleted Successfully'
        
        shops = self.fetch() 
        shop_types = self.fetch_shop_types()
            
        return render_template('settings/my-shops.html', page_title='My Shops', helper=Helper(),
                               shops=shops, shop_types=shop_types, toastr_message=toastr_message )