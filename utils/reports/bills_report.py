import pytz
from datetime import datetime, timedelta
from flask import render_template, request

from utils.customers.customer_bills import CustomerBills
from utils.customers.customers import Customers
from utils.helper import Helper

class BillsReport():
    def __init__(self, db): 
        self.db = db
      
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
        
        customers = Customers(self.db).fetch()
        bills = CustomerBills(self.db).fetch(from_date, to_date, bill_status, customer_id) 
        grand_total = grand_paid = cash_total = mpesa_total =  0
        for bill in bills:
            grand_total = grand_total + bill.total
            grand_paid = grand_paid + bill.paid
            cash_total = cash_total + bill.cash
            mpesa_total = mpesa_total + bill.mpesa
        
        return render_template('reports/bills-report.html', page_title='Reports > Bills', helper=Helper(), menu='reports', sub_menu='bills_report',
                               customers=customers, bills=bills, current_date=current_date, bill_status=bill_status, 
                                from_date=from_date, to_date=to_date, customer_id=customer_id,
                                grand_total=grand_total, grand_paid=grand_paid, cash_total=cash_total, mpesa_total=mpesa_total
                            )