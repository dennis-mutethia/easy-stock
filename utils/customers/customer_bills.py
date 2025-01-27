import pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.entities import Bill
from utils.helper import Helper
from utils.customers.customers import Customers
from utils.customers.payments import Payments
from utils.settings.system_users import SystemUsers

class CustomerBills():
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
            
    def get_bills_to_pay(self, customer_id, paid):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, total-paid bal
            FROM bills
            WHERE total>paid AND customer_id=%s
            ORDER BY id
            """
            params = [customer_id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            bills = []
            for datum in data: 
                pay_amount = datum[1] if paid>datum[1] else paid
                if pay_amount > 0:
                    bill = {
                        'id' : datum[0],
                        'pay_amount' : pay_amount
                    }
                    bills.append(bill)
                paid = paid - pay_amount
                
            return bills
        
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
               
    def __call__(self):
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        from_date = (datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=365)).strftime('%Y-%m-%d') #datetime(datetime.now(pytz.timezone("Africa/Nairobi")).year, 1, 1).strftime('%Y-%m-%d')
        to_date = current_date
        bill_status = 2
        customer_id = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                bill_status = int(request.args.get('bill_status', bill_status))
                customer_id = int(request.args.get('customer_id', customer_id))
            except ValueError as e:
                print(f"Error converting bill_status: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
                
        if request.method == 'POST':       
            if request.form['action'] == 'assign_customer_bill':
                bill_id = int(request.form['bill_id'], 0)
                bill_amount = int(request.form['bill_amount'])     
                customer_id = int(request.form['customer_id'])  
                if bill_id > 0:         
                    self.add(customer_id, bill_amount)
                else:
                    self.update(bill_id, customer_id, bill_amount)
                
            elif request.form['action'] == 'submit_payment':
                bill_id = int(request.form['bill_id'])
                amount_paid = float(request.form['amount_paid'])           
                payment_mode_id = int(request.form['payment_mode_id'])
                
                if bill_id > 0:
                    Payments(self.db).add(bill_id, amount_paid, payment_mode_id)                    
                    self.pay(bill_id, amount_paid) 
                    
                else:
                    customer_id = int(request.args.get('customer_id', customer_id))
                    for bill in self.get_bills_to_pay(customer_id, amount_paid):   
                        Payments(self.db).add(bill['id'], bill['pay_amount'], payment_mode_id)                    
                        self.pay(bill['id'], bill['pay_amount'])                     
        
        customers = Customers(self.db).fetch()
        payment_modes = self.db.fetch_payment_modes()
        bills = self.fetch(from_date, to_date, bill_status, customer_id) 
        grand_total = grand_paid = cash_total = mpesa_total =  0
        for bill in bills:
            grand_total = grand_total + bill.total
            grand_paid = grand_paid + bill.paid
            cash_total = cash_total + bill.cash
            mpesa_total = mpesa_total + bill.mpesa
            
        return render_template('customers/bills.html', page_title='Customer > Debts', helper=Helper(), menu='customers', sub_menu='customer_debts',
                               customers=customers, payment_modes=payment_modes, bills=bills, current_date=current_date, bill_status=bill_status, 
                               from_date=from_date, to_date=to_date, customer_id=customer_id,
                               grand_total=grand_total, grand_paid=grand_paid, cash_total=cash_total, mpesa_total=mpesa_total
                            )