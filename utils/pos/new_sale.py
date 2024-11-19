from datetime import datetime
from flask import render_template, request
from flask_login import current_user
import user_agents

from utils.customers.customers import Customers
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories
from utils.stock.stock_take import StockTake
from utils.pos.bills import Bills
from utils.pos.bill_entries import BillEntries
from utils.pos.payments import Payments

class NewSale():
    def __init__(self, db): 
        self.db = db
    
    def update_bill_entries(self, bill_id):
        self.db.ensure_connection()
        
        query = """
        UPDATE bill_entries
        SET bill_id = %s
        WHERE bill_id=0 AND shop_id=%s AND created_by=%s
        """
        
        params = (bill_id, current_user.shop.id, current_user.id)
        with self.db.conn.cursor() as cursor:
            cursor.execute(query, params)
            self.db.conn.commit()
              
    def __call__(self):
        search = ''
        category_id = 0  
        page = 1   
        in_stock = 0
        bill_id = 0 
        
        if request.method == 'GET':   
            try:    
                search = request.args.get('search', '')
                category_id = int(request.args.get('category_id', 0))
                page = int(request.args.get('page', 1))
                in_stock = int(request.args.get('in_stock', 0))
            except ValueError as e:
                print(f"Error converting category_id: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
        
        if request.method == 'POST':          
            if request.form['action'] == 'submit_bill':
                customer_id = int(request.form['customer_id'])
                amount_paid = float(request.form['amount_paid'])
                payment_mode_id = int(request.form['payment_mode_id'])
                bill_id = Bills(self.db).add(customer_id, amount_paid)
                self.update_bill_entries(bill_id)
                if amount_paid>0:
                    Payments(self.db).add(bill_id, amount_paid, payment_mode_id)

            elif request.form['action'] == 'clear':
                BillEntries(self.db).clear()
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        product_categories = ProductsCategories(self.db).fetch()
        stocks = StockTake(self.db).fetch(current_date, search, category_id, in_stock, page)
        customers = Customers(self.db).fetch()
        payment_modes = self.db.fetch_payment_modes()
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(stocks)==30 else 0
        bill_entries = BillEntries(self.db).fetch(0)
        grandtotal = 0
        for bill_entry in bill_entries:
            grandtotal = grandtotal + (bill_entry.price * bill_entry.qty) 
            
        return render_template('pos/new-sale.html', helper=Helper(),
                               product_categories=product_categories, stocks=stocks, customers=customers, in_stock=in_stock,
                               bill_entries=bill_entries, grandtotal=grandtotal, payment_modes=payment_modes, bill_id=bill_id, 
                               page_title='POS > New Sale', search=search, category_id=category_id, page=page, prev_page=prev_page, next_page=next_page,
                               user_agent=user_agents.parse(request.headers.get('User-Agent')) )
