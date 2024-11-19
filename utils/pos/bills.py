from datetime import datetime
from flask import redirect, render_template, request, url_for
from flask_login import current_user

from utils.customers.customers import Customers
from utils.entities import Bill
from utils.helper import Helper
from utils.pos.bill_entries import BillEntries
from utils.pos.payments import Payments
from utils.settings.system_users import SystemUsers

class Bills():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self, from_date, to_date, bill_status, customer_id=0, page=0):
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
            
            if page>0:
                query = query + """
                ORDER BY id DESC
                LIMIT 50 OFFSET %s
                """
                params.append((page - 1)*50)
            
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
        
    def get_total_unpaid_bills(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT SUM(total - paid) AS total_debts
            FROM bills
            WHERE shop_id = %s AND total != 'Nan'
            """
            params = [current_user.shop.id]
            
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
        VALUES(%s, %s, 0, %s, NOW(), %s)
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
            
    def assign_customer(self, id, customer_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE bills
            SET customer_id=%s, updated_at=NOW(), updated_by=%s
            WHERE id=%s
            """
            params = [customer_id, current_user.shop.id, id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()    
            
    def pay(self, id, paid):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE bills
            SET paid=paid+%s, updated_at=NOW(), updated_by=%s
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
             
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        report_date = current_date
        bill_status = 0 
        page = 1
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', current_date)
                bill_status = int(request.args.get('bill_status', 0))
                page = int(request.args.get('page', 1))
            except ValueError as e:
                print(f"Error converting bill_status: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
                
        if request.method == 'POST':       
            if request.form['action'] == 'assign_customer_bill':
                bill_id = int(request.form['bill_id'])
                customer_id = int(request.form['customer_id'])               
                self.assign_customer(bill_id, customer_id)     
                   
            if request.form['action'] == 'edit':
                bill_id = int(request.form['bill_id'])           
                BillEntries(self.db).edit(bill_id)    
                self.delete(bill_id) 
                Payments(self.db).delete(bill_id)
                return redirect(url_for('posNewSale'))                                  
                
            elif request.form['action'] == 'submit_payment':
                bill_id = int(request.form['bill_id'])
                amount_paid = request.form['amount_paid']                
                payment_mode_id = int(request.form['payment_mode_id'])
                Payments(self.db).add(bill_id, amount_paid, payment_mode_id)                    
                self.pay(bill_id, amount_paid) 
        
        customers = Customers(self.db).fetch()
        payment_modes = self.db.fetch_payment_modes()
        bills = self.fetch(report_date, report_date, bill_status, 0, page)
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(bills)==50 else 0
        grand_total = grand_paid = cash_total = mpesa_total =  0
        for bill in bills:
            grand_total = grand_total + bill.total
            grand_paid = grand_paid + bill.paid
            cash_total = cash_total + bill.cash
            mpesa_total = mpesa_total + bill.mpesa
            
        return render_template('pos/bills.html', page_title='POS > Bills', helper=Helper(),
                               customers=customers, payment_modes=payment_modes, bills=bills, current_date=current_date, bill_status=bill_status, report_date=report_date,
                               grand_total=grand_total, grand_paid=grand_paid, cash_total=cash_total, mpesa_total=mpesa_total,
                               page=page, prev_page=prev_page, next_page=next_page)