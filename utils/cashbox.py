import pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper

class Cash():
    def __init__(self, date, total_sales, paid_bills, new_bills, total_expenses, cash, mpesa):
        self.date = date        
        self.total_sales = total_sales
        self.paid_bills = paid_bills
        self.new_bills = new_bills
        self.total_expenses = total_expenses
        self.cash = cash
        self.mpesa = mpesa
        
class CashBox():
    def __init__(self, db): 
        self.db = db

    def fetch(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """                       
            WITH all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions, 
                    selling_price
                FROM stock
                WHERE shop_id = %s 
                AND EXTRACT(MONTH FROM stock_date) = EXTRACT(MONTH FROM %s::date)
                AND EXTRACT(YEAR FROM stock_date) = EXTRACT(YEAR FROM %s::date)
            ),
            sales AS(
                SELECT 
                    today.stock_date, 
                    today.selling_price,
                    (today.opening + today.additions - tomorrow.opening) AS sold
                FROM all_stock AS today
                INNER JOIN all_stock AS tomorrow ON tomorrow.product_id = today.product_id
                    AND DATE(tomorrow.stock_date) = DATE(today.stock_date) + 1
            ),
            totals AS(
                SELECT stock_date, SUM(sold*selling_price) AS total_sales
                FROM sales  
                GROUP BY stock_date
            ),
            exp AS(
                SELECT date, SUM(amount) total_expenses
                FROM expenses
                WHERE shop_id = %s
                GROUP BY date
            ),
            payments AS(
                SELECT DATE(created_at) AS date, SUM(amount) paid_bills
                FROM payments
                WHERE shop_id = %s
                GROUP BY DATE(created_at)                
            ),
            bills AS(
                SELECT DATE(created_at) AS date, SUM(total) new_bills
                FROM bills
                WHERE shop_id = %s
                GROUP BY DATE(created_at)     
            ),            
            received AS(
                SELECT date, cash, mpesa
                FROM cashbox
                WHERE shop_id = %s
                GROUP BY date, cash, mpesa    
            ),
            source AS(
                SELECT stock_date, COALESCE(total_sales,0) AS total_sales, COALESCE(total_expenses,0) AS total_expenses, 
                    COALESCE(paid_bills,0) AS paid_bills, COALESCE(new_bills,0) AS new_bills, COALESCE(cash,0) AS cash, COALESCE(mpesa,0) AS mpesa
                FROM totals
                LEFT JOIN exp ON exp.date=totals.stock_date 
                LEFT JOIN payments ON payments.date=totals.stock_date 
                LEFT JOIN bills ON bills.date=totals.stock_date    
                LEFT JOIN received ON received.date=totals.stock_date    
                ORDER BY stock_date  
            )
            SELECT 
                stock_date, 
                total_sales,
                paid_bills,
                new_bills,
                total_expenses,
                cash,
                mpesa
            FROM source
            """
            params = [current_user.shop.id, report_date, report_date, current_user.shop.id, current_user.shop.id, current_user.shop.id, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            cashes = []
            for datum in data:           
                cashes.append(Cash(datum[0], datum[1], datum[2], datum[3], datum[4], datum[5], datum[6]))

            return cashes 
    
    def update(self, report_date, cash, mpesa):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            INSERT INTO cashbox (date, cash, mpesa, shop_id, created_at, created_by)               
            VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
            ON CONFLICT (date, shop_id) DO UPDATE 
            SET cash = EXCLUDED.cash, mpesa = EXCLUDED.mpesa, updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', updated_by = %s
            RETURNING id
            """
            params = [report_date, cash, mpesa, current_user.shop.id, current_user.id, current_user.id]
            
            try:
                cursor.execute(query, tuple(params))
                self.db.conn.commit()
                id = cursor.fetchone()[0]
                return id
            except Exception as e:
                self.db.conn.rollback()
                print(f"Error updating cashbox: {e}")
                return None
                 
    def __call__(self):
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')
        report_date = max_date
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', report_date)
                
            except Exception as e:
                print(f"An error occurred: {e}")    
        
        if request.method == 'POST':       
            if request.form['action'] == 'update':
                report_date = request.form['report_date']
                cash = request.form['cash']
                mpesa = request.form['mpesa']     
                self.update(report_date, cash, mpesa)              
        
        data = self.fetch(report_date) 
        today = {}
        total_received = total_expected = total_diff = 0
        
        for datum in data:
            if str(datum.date) == report_date:
                today = datum 
                total_expected = today.total_sales + today.paid_bills - today.new_bills + today.total_expenses
                total_received = today.cash + today.mpesa   
                total_diff = total_received - total_expected          
        
        return render_template('cashbox.html', page_title='Cashbox', helper=Helper(), menu = 'cashbox',
                               data=data, today=today, total_expected=total_expected, total_received=total_received, total_diff=total_diff,
                               report_date=report_date, max_date=max_date)