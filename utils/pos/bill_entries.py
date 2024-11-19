from flask import render_template, request
from flask_login import current_user

from utils.entities import BillEntry
from utils.helper import Helper

class BillEntries():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self, bill_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, bill_id, stock_id, item_name, price, qty
            FROM bill_entries
            WHERE shop_id=%s AND bill_id=%s AND qty>0
            """
            params = [current_user.shop.id, bill_id]
            
            if bill_id==0:
                query = query + " AND created_by=%s"
                params.append(current_user.id)
                
            query = query + " ORDER BY id"
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            bill_entries = []
            for bill_entry in data:
                bill_entries.append(BillEntry(bill_entry[0], bill_entry[1], bill_entry[2], bill_entry[3], bill_entry[4], bill_entry[5]))

            return bill_entries
         
    def get_total(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH b AS(
                SELECT id FROM bills
                WHERE DATE(created_at) = DATE(%s) AND shop_id = %s AND id>0
            ),
            bps AS(
                SELECT id, purchase_price
                FROM stock 
                WHERE DATE(stock_date) = DATE(%s) AND shop_id = %s
            ),
            be AS(
                SELECT purchase_price*qty AS bp, price*qty AS sp
                FROM bill_entries
                INNER JOIN b ON b.id = bill_entries.bill_id
                INNER JOIN bps ON bps.id = bill_entries.stock_id
                WHERE qty>0
            )
            SELECT SUM(bp) cost, SUM(sp) AS sales FROM be
            """
            params = [report_date, current_user.shop.id, report_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchone()
            if data:
                return int(data[0]) if data[0] is not None and isinstance(data[0], (int, float)) else 0, int(data[1]) if data[1] is not None and isinstance(data[1], (int, float)) else 0
            else:
                return None
            
    def edit(self, bill_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE bill_entries
            SET bill_id=0, updated_at=NOW(), updated_by=%s
            WHERE bill_id=%s
            """
            params = [current_user.shop.id, bill_id]
            cursor.execute(query, tuple(params))
            self.db.conn.commit()    
                   
    def add(self, bill_id, stock_id, item_name, price, qty):
        price = price.replace(',', '')
        self.db.ensure_connection()
        
        query = """
        INSERT INTO bill_entries(bill_id, stock_id, item_name, price, qty, shop_id, created_at, created_by) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s) 
        ON CONFLICT (bill_id, stock_id, created_by) DO UPDATE 
        SET price = EXCLUDED.price, qty = EXCLUDED.qty, updated_at = NOW(), updated_by = %s
        RETURNING id
        """

        params = (bill_id, stock_id, item_name.upper(), price, qty, current_user.shop.id, current_user.id, current_user.id)

        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(query, params)
                self.db.conn.commit()
                row_id = cursor.fetchone()[0]
                return row_id
        except Exception as e:
            self.db.conn.rollback()
            raise e
            
    def clear(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            DELETE FROM bill_entries
            WHERE bill_id=0 AND shop_id=%s AND created_by=%s
            """
            cursor.execute(query, (current_user.shop.id, current_user.id))
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
                #self.delete(id) 
                
        bill_entries = self.fetch(0)
        grandtotal = 0
        for bill_entry in bill_entries:
            grandtotal = grandtotal + (bill_entry.price * bill_entry.qty) 
            
        return render_template('pos/bill-entries.html', helper=Helper(), 
                               bill_entries=bill_entries, grandtotal=grandtotal )