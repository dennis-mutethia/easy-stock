import pytz, os, uuid, psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_login import current_user

from utils.entities import Company, License, Package, PaymentMode, Shop

# Load once at module level, not per instantiation
load_dotenv()

class Db():
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.conn = None
        self.ensure_connection()
    
    def ensure_connection(self):
        """Reconnect only if connection is closed or broken.
        Avoids the extra SELECT 1 round trip on healthy connections."""
        if self.conn is not None and not self.conn.closed:
            return  # Already healthy — skip entirely
        try:
            self.conn = psycopg2.connect(self.database_url)
        except Exception as e:
            print(f"DB connection error: {e}")
            raise

    def _execute_write(self, query, params):
        """DRY helper for INSERT/UPDATE that commits and returns the first column of the first row."""
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(query, params)
                self.conn.commit()
                row = cursor.fetchone()
                return row[0] if row else None
            except Exception as e:
                self.conn.rollback()
                print(f"Write error: {e}")
                raise
                        
    def migration(self):
        self.ensure_connection()
        for filename in ("db_schema.sql", "db_data.sql"):
            with open(filename, "r") as f:
                sql_script = f.read()
            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(sql_script)
                    self.conn.commit()
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"Error executing {filename}: {e}")
                raise
    
    def save_payment(self, bill_id, amount, payment_mode_id):
        return self._execute_write(
            """
            INSERT INTO payments(bill_id, amount, payment_mode_id, created_at, created_by) 
            VALUES(%s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 0) 
            RETURNING id
            """,
            (bill_id, amount, payment_mode_id)
        )
    
    def save_license(self, package, payment_id):
        return self._execute_write(
            """
            INSERT INTO licenses(key, package_id, payment_id, expires_at, created_at, created_by) 
            VALUES(%s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' + INTERVAL %s, 
                   CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 0)
            RETURNING id
            """,
            (str(uuid.uuid4()), package.id, payment_id, f'+{package.validity} DAYS')
        )
    
    def update_license(self, license_id, package_id):
        package = self.get_package_by_id(package_id)
        return self._execute_write(
            """
            UPDATE licenses 
            SET 
                package_id = %s, 
                expires_at = CASE 
                                WHEN expires_at > CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' 
                                THEN expires_at + INTERVAL %s 
                                ELSE CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' + INTERVAL %s 
                            END, 
                updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 
                updated_by = %s 
            WHERE id = %s
            """,
            (package_id, f'+{package.validity} DAYS', f'+{package.validity} DAYS', current_user.id, license_id)
        )
    
    def save_company(self, name, license_id):
        return self._execute_write(
            """
            INSERT INTO companies(name, license_id, created_at, created_by) 
            VALUES(%s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 0) 
            RETURNING id
            """,
            (name.upper(), license_id)
        )

    def _fetch_one(self, query, params=()):
        """DRY helper for SELECT queries returning a single row."""
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def _fetch_all(self, query, params=()):
        """DRY helper for SELECT queries returning multiple rows."""
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_license_by_id(self, id):
        row = self._fetch_one(
            """
            SELECT id, key, package_id, DATE(expires_at), 
                   expires_at > NOW(), 
                   EXTRACT(DAY FROM (expires_at - NOW()))
            FROM licenses WHERE id = %s
            """,
            (id,)
        )
        return License(*row) if row else None
      
    def get_company_by_id(self, id):
        row = self._fetch_one(
            "SELECT id, name, license_id FROM companies WHERE id = %s",
            (id,)
        )
        return Company(*row) if row else None
      
    def get_company_shops(self):
        rows = self._fetch_all(
            """
            SELECT id, name, shop_type_id, company_id, location, 
                   phone_1, phone_2, paybill, account_no, till_no
            FROM shops WHERE company_id = %s
            """,
            (current_user.company.id,)
        )
        return [Shop(*row) for row in rows]
        
    def get_package_by_id(self, id):
        row = self._fetch_one(
            "SELECT id, name, amount, description, color, validity, pay FROM packages WHERE id = %s",
            (id,)
        )
        return Package(*row) if row else None
            
    def fetch_payment_modes(self):
        rows = self._fetch_all("SELECT id, name FROM payment_modes")
        return [PaymentMode(*row) for row in rows]
          
    def get_payment_mode_by_id(self, id):
        row = self._fetch_one(
            "SELECT id, name FROM payment_modes WHERE id = %s",
            (id,)
        )
        return PaymentMode(*row) if row else None
    
    def import_product_categories_template_data(self, shop_id, shop_type_id):
        self._execute_write(
            """
            WITH source AS (
                SELECT name FROM product_categories WHERE shop_id = %s
            )
            INSERT INTO product_categories(name, shop_id, created_at, created_by)
            SELECT name, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s
            FROM source
            """,
            (0 - int(shop_type_id), shop_id, current_user.id)
        )
    
    def import_products_template_data(self, shop_id, shop_type_id):
        self._execute_write(
            """
            WITH pc AS (
                SELECT id, name, shop_id FROM product_categories
            ),
            source AS (
                SELECT products.name, products.purchase_price, products.selling_price, pc_2.id AS category_id
                FROM products
                JOIN pc AS pc_1 ON pc_1.id = products.category_id
                JOIN pc AS pc_2 ON pc_2.name = pc_1.name AND pc_2.shop_id = %s
                WHERE products.shop_id = %s
            )
            INSERT INTO products(name, purchase_price, selling_price, category_id, shop_id, created_at, created_by)
            SELECT name, purchase_price, selling_price, category_id, %s, 
                   CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s
            FROM source
            """,
            (shop_id, 0 - int(shop_type_id), shop_id, current_user.id)
        )
            
    def create_current_month_partition(self):
        self.ensure_connection()
        nairobi = pytz.timezone("Africa/Nairobi")
        current_date = datetime.now(nairobi).replace(day=1)
        next_month = (current_date + timedelta(days=31)).replace(day=1)
        partition_name = f"stock_{current_date.year}_{current_date.month:02d}"

        # Partition names can't be parameterised in psycopg2 — values are
        # datetime-derived so interpolation is safe here
        query = f"""
            CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF stock
            FOR VALUES FROM ('{current_date.strftime("%Y-%m-%d")}') 
            TO ('{next_month.strftime("%Y-%m-%d")}');
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            self.conn.commit()
            print(f"Partition {partition_name} created.")