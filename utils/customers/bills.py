from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.customers.customers import Customers
from utils.entities import Bill
from utils.helper import Helper
from utils.customers.payments import Payments
from utils.settings.system_users import SystemUsers

class Bills():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self, from_date, to_date, bill_status, customer_id=0):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, total, paid, DATE(created_at) AS created_at, customer_id, created_by
            FROM bills
            WHERE (DATE(created_at) BETWEEN DATE(%s) AND DATE(%s)) AND shop_id = %s AND total != 'Nan'
            """
            params = [from_date, to_date, current_user.shop.id]
            
            if bill_status==1:
                query = query + " AND paid>=total"
            if bill_status==2:
                query = query + " AND paid<total"
                
            if customer_id>0:
                query = query + " AND customer_id=%s"
                params.append(customer_id)
            
            query = query + """
            ORDER BY id DESC
            """
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            bills = []
            for datum in data:                
                customer = Customers(self.db).fetch_by_id(datum[4])
                user = SystemUsers(self.db).get_by_id(datum[5])  
                payments = Payments(self.db).fetch_by_bill_id(datum[0])         
                bills.append(Bill(datum[0], datum[1], datum[2], datum[3], customer, user, payments))

            return bills 
               
    def fetch_by_id(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, total, paid, TO_CHAR(created_at + INTERVAL '3 HOURS', 'YYYY-MM-DD HH24:MI') AS created_at, customer_id, created_by
            FROM bills
            WHERE id = %s AND total != 'Nan'
            """
            params = [id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchone()
            if data:
                customer = Customers(self.db).fetch_by_id(data[4])
                user = SystemUsers(self.db).get_by_id(data[5])
                payments = Payments(self.db).fetch_by_bill_id(data[0])
                return Bill(data[0], data[1], data[2], data[3], customer, user, payments)
            else:
                return None   
        
    def get_total_unpaid_bills(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT SUM(total - paid) AS total_debts
            FROM bills
            WHERE shop_id = %s AND total != 'Nan' AND DATE(created_at) <= %s
            """
            params = [current_user.shop.id, report_date]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchone()
            if data:
                return int(data[0]) if data[0] is not None and isinstance(data[0], (int, float)) else 0
            else:
                return None
            
    def add(self, customer_id, bill_amount):
        self.db.ensure_connection()            
        query = """
        INSERT INTO bills(customer_id, total, paid, shop_id, created_at, created_by) 
        VALUES(%s, %s, 0, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s)
        RETURNING id
        """

        params = (customer_id, bill_amount, current_user.shop.id, current_user.id)
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                self.db.conn.commit()
                row_id = cursor.fetchone()[0]
                return row_id
        except Exception as e:
            self.db.conn.rollback()
            raise e        
            
    def update(self, id, customer_id, bill_amount):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE bills
            SET customer_id=%s, total=%s, updated_at=CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', updated_by=%s
            WHERE id=%s
            """
            params = [customer_id, bill_amount, current_user.shop.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()    
            
    def pay(self, id, paid):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE bills
            SET paid=paid+%s, updated_at=CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', updated_by=%s
            WHERE id=%s
            """
            params = [paid, current_user.shop.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()
    
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM bills
            WHERE id=%s
            """
            params = [id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()    
     