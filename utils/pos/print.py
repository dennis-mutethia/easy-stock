from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.pos.bill_entries import BillEntries
from utils.pos.bills import Bills

class Print():
    def __init__(self, db): 
        self.db = db
            
    def __call__(self):   
        bill_id = int(request.args.get('bill_id', 0))
        show_vat = int(request.args.get('show_vat', 0))
  
        bill = Bills(self.db).fetch_by_id(bill_id)
        bill_entries = BillEntries(self.db).fetch(bill_id)
            
        return render_template('pos/print.html', bill_id=bill_id, show_vat=show_vat, helper=Helper(),
                               bill=bill, bill_entries=bill_entries)