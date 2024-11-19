from datetime import datetime, timedelta
from flask import redirect, render_template, request, url_for
from flask_login import current_user

from utils.helper import Helper
from utils.customers.customers import Customers
from utils.pos.bill_entries import BillEntries
from utils.pos.bills import Bills
from utils.pos.payments import Payments

class CustomerBills():
    def __init__(self, db): 
        self.db = db
    
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
               
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d') #datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
        to_date = current_date
        bill_status = 2
        customer_id = 0
        page = 1
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                bill_status = int(request.args.get('bill_status', bill_status))
                customer_id = int(request.args.get('customer_id', customer_id))
                page = int(request.args.get('page', 1))
            except ValueError as e:
                print(f"Error converting bill_status: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
                
        if request.method == 'POST':       
            if request.form['action'] == 'assign_customer_bill':
                bill_amount = int(request.form['bill_amount'])     
                customer_id = int(request.form['customer_id'])              
                Bills(self.db).add(customer_id, bill_amount)
                   
            if request.form['action'] == 'edit':
                bill_id = int(request.form['bill_id'])           
                BillEntries(self.db).edit(bill_id)     
                Bills(self.db).delete(bill_id)  
                Payments(self.db).delete(bill_id)
                return redirect(url_for('posNewSale'))               
                
            elif request.form['action'] == 'submit_payment':
                bill_id = int(request.form['bill_id'])
                amount_paid = float(request.form['amount_paid'])           
                payment_mode_id = int(request.form['payment_mode_id'])
                
                if bill_id > 0:
                    Payments(self.db).add(bill_id, amount_paid, payment_mode_id)                    
                    Bills(self.db).pay(bill_id, amount_paid) 
                    
                else:
                    customer_id = int(request.args.get('customer_id', customer_id))
                    for bill in self.get_bills_to_pay(customer_id, amount_paid):   
                        Payments(self.db).add(bill['id'], bill['pay_amount'], payment_mode_id)                    
                        Bills(self.db).pay(bill['id'], bill['pay_amount']) 
                    
        
        customers = Customers(self.db).fetch()
        payment_modes = self.db.fetch_payment_modes()
        bills = Bills(self.db).fetch(from_date, to_date, bill_status, customer_id, page) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(bills)==50 else 0
        grand_total = grand_paid = cash_total = mpesa_total =  0
        for bill in bills:
            grand_total = grand_total + bill.total
            grand_paid = grand_paid + bill.paid
            cash_total = cash_total + bill.cash
            mpesa_total = mpesa_total + bill.mpesa
            
        return render_template('customers/bills.html', page_title='Customer > Bills', helper=Helper(),
                               customers=customers, payment_modes=payment_modes, bills=bills, current_date=current_date, bill_status=bill_status, 
                               from_date=from_date, to_date=to_date, customer_id=customer_id,
                               grand_total=grand_total, grand_paid=grand_paid, cash_total=cash_total, mpesa_total=mpesa_total,
                               page=page, prev_page=prev_page, next_page=next_page)