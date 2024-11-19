from flask import render_template, request
from flask_login import current_user

from utils.entities import Bill, BillEntry, Payment
from utils.helper import Helper
from utils.settings.system_users import SystemUsers

class Payments():
    def __init__(self, db): 
        self.db = db
            
    def fetch_by_bill_id(self, bill_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, bill_id, amount, payment_mode_id, TO_CHAR(created_at + INTERVAL '3 HOURS', 'YYYY-MM-DD HH24:MI') AS created_at, created_by
            FROM payments
            WHERE bill_id = %s
            """
            params = [bill_id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            payments = []
            for datum in data:
                payment_mode = self.db.get_payment_mode_by_id(datum[3])
                user = SystemUsers(self.db).get_by_id(datum[5])                
                payments.append(Payment(datum[0], datum[1], datum[2], datum[4], user, payment_mode))

            return payments 
            
    def add(self, bill_id, amount, payment_mode_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:              
            query = """
            INSERT INTO payments(bill_id, amount, payment_mode_id, shop_id, created_at, created_by) 
            VALUES(%s, %s, %s, %s, NOW(), %s) 
            RETURNING id
            """
            params = (bill_id, amount, payment_mode_id, current_user.shop.id, current_user.id)
            try:
                with self.db.conn.cursor() as cursor:
                    cursor.execute(query, params)
                    self.db.conn.commit()
                    row_id = cursor.fetchone()[0]
                    return row_id
            except Exception as e:
                self.db.conn.rollback()
                raise e
    
    
    def delete(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM payments
            WHERE id=%s
            """
            params = [id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()    
                       
    def __call__(self):
        if request.method == 'POST':       
            if request.form['action'] == 'add':
                stock_id = request.form['stock_id']    
                bill_id = request.form['bill_id']
                item_name = request.form['item_name']    
                price = request.form['price']       
                qty = request.form['qty']    
                self.add(bill_id, stock_id, item_name, price, qty)
                return 'success'                
                
            elif request.form['action'] == 'delete':
                id = request.form['item_id']
                self.delete(id) 
                
        bill_entries = self.fetch(0)
        grandtotal = 0
        for bill_entry in bill_entries:
            grandtotal = grandtotal + (bill_entry.price * bill_entry.qty) 
            
        return render_template('pos/bill-entries.html', helper=Helper(), 
                               bill_entries=bill_entries, grandtotal=grandtotal )