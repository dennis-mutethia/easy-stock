from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Expense, User, UserLevel
from utils.helper import Helper
from utils.settings.my_shops import MyShops

class SystemUsers():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, phone, user_level_id, shop_id
            FROM users 
            WHERE shop_id IN(
                SELECT id FROM shops WHERE company_id = %s
            )
            """
            params = [current_user.company.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            users = []
            for datum in data:      
                user_level = self.get_user_level_id(datum[3])
                shop = MyShops(self.db).get_by_id(datum[4]) 
                company = self.db.get_company_by_id(shop.company_id)
                license = self.db.get_license_by_id(company.license_id)   
                users.append(User(datum[0], datum[1], datum[2], user_level, shop, company, license))

            return users 
               
    def get_by_id(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, phone, user_level_id, shop_id
            FROM users 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                user_level = self.get_user_level_id(data[3])
                shop = MyShops(self.db).get_by_id(data[4])
                company = self.db.get_company_by_id(shop.company_id)
                license = self.db.get_license_by_id(company.license_id)   
                return User(data[0], data[1], data[2], user_level, shop, company, license)
            else:
                return None      
    
    def get_by_phone(self, phone):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, phone, user_level_id, shop_id
            FROM users 
            WHERE phone = %s 
            """
            cursor.execute(query, (phone,))
            data = cursor.fetchone()
            if data:
                user_level = self.get_user_level_id(data[3])
                shop = MyShops(self.db).get_by_id(data[4])
                company = self.db.get_company_by_id(shop.company_id)
                license = self.db.get_license_by_id(company.license_id)   
                return User(data[0], data[1], data[2], user_level, shop, company, license)
            else:
                return None    
           
    def authenticate(self, phone, password):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, phone, user_level_id, shop_id
            FROM users 
            WHERE phone = %s AND password = %s 
            """
            cursor.execute(query, (phone, Helper().hash_password(password)))
            data = cursor.fetchone()
            if data:
                user_level = self.get_user_level_id(data[3])
                shop = MyShops(self.db).get_by_id(data[4])
                company = self.db.get_company_by_id(shop.company_id)
                license = self.db.get_license_by_id(company.license_id)   
                return User(data[0], data[1], data[2], user_level, shop, company, license)
            else:
                return None 
    
    def add(self, name, phone, user_level_id, shop_id, password):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO users(name, phone, user_level_id, shop_id, password, created_at, created_by) 
            VALUES(%s, %s, %s, %s, %s, NOW(), 0)
            RETURNING id
            """
            cursor.execute(query, (name.upper(), phone, user_level_id, shop_id, Helper().hash_password(password)))
            self.db.conn.commit()
            user_id = cursor.fetchone()[0]
            return user_id  
            
    def update(self, user_id, name, phone, user_level_id, shop_id, password):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE users 
            SET name = %s, phone = %s, user_level_id = %s, shop_id = %s, updated_by = %s, updated_at=NOW()            
            """
            params = [name.upper(), phone, user_level_id, shop_id, current_user.id]
            if password is not None:
                query = query + ", password = %s"
                params.append(Helper().hash_password(password))
            
            query = query + " WHERE id=%s"
            params.append(user_id)
            
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
            
    def reset_password(self, phone):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE users 
            SET password = %s, updated_by = %s, updated_at=NOW()   
            WHERE phone = %s         
            """
            params = [Helper().hash_password(phone), current_user.id, phone]            
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
            
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM users
            WHERE id=%s
            """
            cursor.execute(query, (id,))
            self.db.conn.commit()
      
    def fetch_user_levels(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, level, description
            FROM user_levels 
            WHERE id >= %s
            ORDER BY id
            """
            cursor.execute(query, (current_user.user_level.id,))
            data = cursor.fetchall()
            user_levels = []
            for datum in data:      
                user_levels.append(UserLevel(datum[0], datum[1], datum[2], datum[3].replace('\\n','')))

            return user_levels 
        
    def get_user_level_id(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, level, description
            FROM user_levels 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return UserLevel(data[0], data[1], data[2], data[3])
            else:
                return None    
               
    def __call__(self):                
        if request.method == 'POST':       
            if request.form['action'] == 'add':
                name = request.form['name']
                phone = request.form['phone']      
                user_level_id = request.form['user_level_id']     
                shop_id = request.form['shop_id']     
                self.add(name, phone, user_level_id, shop_id, password=phone)
                   
            if request.form['action'] == 'update':
                user_id = request.form['user_id']
                name = request.form['name']
                phone = request.form['phone']      
                user_level_id = request.form['user_level_id']     
                shop_id = request.form['shop_id']                     
                self.update(user_id, name, phone, user_level_id, shop_id, password=None)
                
            if request.form['action'] == 'reset_password':
                phone = request.form['phone']                    
                self.reset_password(phone)                 
                
            elif request.form['action'] == 'delete':
                user_id = request.form['user_id']
                self.delete(user_id)
                
                
        users = self.fetch() 
        user_levels = self.fetch_user_levels()
        company_shops = self.db.get_company_shops()
            
        return render_template('settings/system-users.html', page_title='System Users', helper=Helper(),
                               users=users, user_levels=user_levels, company_shops=company_shops )