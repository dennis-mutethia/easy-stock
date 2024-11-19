from flask import render_template, request

from utils.helper import Helper
from utils.pos.bill_entries import BillEntries
from utils.pos.bills import Bills
from utils.pos.payments import Payments

class BillDetails():
    def __init__(self, db): 
        self.db = db
    
    def __call__(self):
        bill_id = int(request.args.get('bill_id', 0))
                
        bill = Bills(self.db).fetch_by_id(bill_id)
        bill_entries = BillEntries(self.db).fetch(bill_id)
        payments = Payments(self.db).fetch_by_bill_id(bill_id)
            
        return render_template('pos/bill-details.html', helper=Helper(), 
                               bill=bill, bill_entries=bill_entries, payments=payments )