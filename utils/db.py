from flask_login import current_user
import os, uuid, psycopg2

from utils.entities import Company, License, Package, PaymentMode, Shop, ShopType, User, UserLevel
from utils.helper import Helper

class Db():
    def __init__(self):
        # Access the environment variables
        self.conn_params = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'),
            'port': os.getenv('DB_PORT'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        self.conn = None
        self.ensure_connection()
    
    def ensure_connection(self):
        try:
            # Check if the connection is open
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(**self.conn_params)
            else:
                # Test the connection
                with self.conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
        except Exception as e:
            # Reconnect if the connection is invalid
            self.conn = psycopg2.connect(**self.conn_params)
                   
    def create_base_tables(self):
        try:
            self.ensure_connection()  # Ensure your connection to PostgreSQL is established
            
            # Read the SQL script file
            with open("pos.sql", "r") as f:
                sql_script = f.read()
                
                # Execute the SQL script
                with self.conn.cursor() as cursor:
                    cursor.execute(sql_script)
                    self.conn.commit()
                
        except psycopg2.Error as e:
            print(f"Error executing SQL script: {e}")
    
    def load_shop_template_data(self, shop_id):        
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            INSERT INTO product_categories(name, shop_id, created_at, created_by)
            SELECT name, ?, NOW(), ? FROM product_categories WHERE shop_id = 0
            """
            cursor.execute(query, (shop_id, current_user.id))
            self.conn.commit()            
            
            query = """
            INSERT INTO products(name, purchase_price, selling_price, category_id, shop_id, created_at, created_by)
            SELECT name, purchase_price, selling_price, category_id, ?, NOW(), ? FROM products WHERE shop_id = 0
            """
            cursor.execute(query, (shop_id, current_user.id))
            self.conn.commit()
        
    def save_payment(self, bill_id, amount, payment_mode_id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            INSERT INTO payments(bill_id, amount, payment_mode_id, created_at, created_by) 
            VALUES(%s, %s, %s, NOW(), 0) 
            RETURNING id
            """
            cursor.execute(query, (bill_id, amount, payment_mode_id))
            self.conn.commit()
            payment_id = cursor.fetchone()[0]
            return payment_id 
    
    def save_license(self, package, payment_id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            key = uuid.uuid4()
            query = """
            INSERT INTO licenses(key, package_id, payment_id, expires_at, created_at, created_by) 
            VALUES(%s, %s, %s, NOW() + INTERVAL %s, NOW(), 0)
            RETURNING id
            """
            cursor.execute(query, (str(key), package.id, payment_id, f'+{package.validity} DAYS'))
            self.conn.commit()
            license_id = cursor.fetchone()[0]
            return license_id
    
    def save_company(self, name, license_id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            INSERT INTO companies(name, license_id, created_at, created_by) 
            VALUES(%s, %s, NOW(), 0) 
            RETURNING id
            """
            cursor.execute(query, (name.upper(), license_id))
            self.conn.commit()
            company_id = cursor.fetchone()[0]
            return company_id 
      
    def get_license_by_id(self, id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            SELECT id, key, package_id, DATE(expires_at), expires_at > NOW(), EXTRACT(DAY FROM (expires_at - NOW()))
            FROM licenses 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return License(data[0], data[1], data[2], data[3], data[4], data[5])
            else:
                return None    
      
    def get_company_by_id(self, id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            SELECT id, name, license_id
            FROM companies 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return Company(data[0], data[1], data[2])
            else:
                return None    
      
    def get_company_shops(self):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            SELECT id, name, shop_type_id, company_id, location, phone_1, phone_2, paybill, account_no, till_no
            FROM shops 
            WHERE company_id = %s 
            """
            cursor.execute(query, (current_user.company.id,))
            data = cursor.fetchall()
            shops = []
            for datum in data:
                shops.append(Shop(datum[0], datum[1], datum[2], datum[3], datum[4], datum[5], datum[6], datum[7], datum[8], datum[9]))
            
            return shops
        
    def get_package_by_id(self, id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            SELECT id, name, amount, description, color, validity
            FROM packages 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return Package(data[0], data[1], data[2], data[3], data[4], data[5])
            else:
                return None   
            
    def fetch_payment_modes(self):
        self.ensure_connection() 
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT id, name, account FROM payment_modes")
            data = cursor.fetchall()
            payment_modes = []
            for payment_mode in data:
                payment_modes.append(PaymentMode(payment_mode[0], payment_mode[1], payment_mode[2]))
                
            return payment_modes
          
    def get_payment_mode_by_id(self, id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            SELECT id, name, account
            FROM payment_modes 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return PaymentMode(data[0], data[1], data[2])
            else:
                return None       