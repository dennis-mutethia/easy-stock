import pytz, os, uuid, psycopg2
from datetime import datetime, timedelta
from flask_login import current_user

from utils.entities import Company, License, Package, PaymentMode, Shop

class Db():
    def __init__(self):
        # Access the environment variables
        self.conn_params = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
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
                   
    def migration(self):
        try:
            self.ensure_connection()  # Ensure your connection to PostgreSQL is established
            
            # Read the SQL script file
            with open("db_schema.sql", "r") as f:
                sql_script = f.read()
                
                # Execute the SQL script
                with self.conn.cursor() as cursor:
                    cursor.execute(sql_script)
                    self.conn.commit()
            
            # Read the SQL script file
            with open("db_data.sql", "r") as f:
                sql_script = f.read()
                
                # Execute the SQL script
                with self.conn.cursor() as cursor:
                    cursor.execute(sql_script)
                    self.conn.commit()
                
        except psycopg2.Error as e:
            print(f"Error executing SQL script: {e}")
    
    def save_payment(self, bill_id, amount, payment_mode_id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            INSERT INTO payments(bill_id, amount, payment_mode_id, created_at, created_by) 
            VALUES(%s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 0) 
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
            VALUES(%s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' + INTERVAL %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 0)
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
            VALUES(%s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 0) 
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
            SELECT id, name, amount, description, color, validity, pay
            FROM packages 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return Package(data[0], data[1], data[2], data[3], data[4], data[5], data[6])
            else:
                return None   
            
    def fetch_payment_modes(self):
        self.ensure_connection() 
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM payment_modes")
            data = cursor.fetchall()
            payment_modes = []
            for payment_mode in data:
                payment_modes.append(PaymentMode(payment_mode[0], payment_mode[1]))
                
            return payment_modes
          
    def get_payment_mode_by_id(self, id):
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            SELECT id, name
            FROM payment_modes 
            WHERE id = %s 
            """
            cursor.execute(query, (id,))
            data = cursor.fetchone()
            if data:
                return PaymentMode(data[0], data[1])
            else:
                return None       
    
    def import_product_categories_template_data(self, shop_id, shop_type_id):
        shop_type_id =  0 - int(shop_type_id)
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
            WITH source AS(
                SELECT name
                FROM product_categories
                WHERE shop_id = %s
            )
            INSERT INTO product_categories(name, shop_id, created_at, created_by)
            SELECT name, %s AS shop_id, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s AS created_by
            FROM source            
            """
            params = [shop_type_id, shop_id, current_user.id]
            cursor.execute(query, tuple(params))
            self.conn.commit()
    
    def import_products_template_data(self, shop_id, shop_type_id):   
        shop_type_id =  0 - int(shop_type_id)
        self.ensure_connection()
        with self.conn.cursor() as cursor:         
            query = """
            WITH pc AS (
                SELECT id, name, shop_id 
                FROM product_categories
            ),
            source AS(
                SELECT products.name, products.purchase_price, products.selling_price, pc_2.id AS category_id
                FROM products
                JOIN pc AS pc_1 ON pc_1.id = products.category_id
                JOIN pc AS pc_2 ON pc_2.name = pc_1.name AND pc_2.shop_id = %s
                WHERE products.shop_id = %s
            )            
            INSERT INTO products(name, purchase_price, selling_price, category_id, shop_id, created_at, created_by)
            SELECT name, purchase_price, selling_price, category_id, %s AS shop_id, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s AS created_by
            FROM source            
            """
            params = [shop_id, shop_type_id, shop_id, current_user.id]
            cursor.execute(query, tuple(params))
            self.conn.commit()
            
    def create_current_month_partition(self):        
        self.ensure_connection()
        with self.conn.cursor() as cursor:  
            # Get the first day of the current month
            current_date = datetime.now(pytz.timezone("Africa/Nairobi")).replace(day=1)

            # Get the first day of the next month
            next_month = (current_date + timedelta(days=31)).replace(day=1)

            # Partition name based on current month
            partition_name = f"stock_{current_date.year}_{current_date.month:02d}"       
            query = f"""
            CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF stock
            FOR VALUES FROM ('{current_date.strftime("%Y-%m-%d")}') 
            TO ('{next_month.strftime("%Y-%m-%d")}');     
            """
            cursor.execute(query)
            self.conn.commit()
            print(f"Partition {partition_name} created successfully.")
           