import pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.entities import Profit
from utils.helper import Helper

class ProfitReport():
    def __init__(self, db): 
        self.db = db
    
    def fetch(self, from_date, to_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """                       
            WITH all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    COALESCE(opening, 0) AS opening, 
                    COALESCE(additions, 0) AS additions, 
                    purchase_price,
                    selling_price
                FROM stock
                WHERE shop_id = %s AND DATE(stock_date) BETWEEN DATE(%s) AND DATE(%s) + 1
            ),
            sales AS(
                SELECT 
                    today.stock_date AS report_date, 
                    today.purchase_price,
                    today.selling_price,
                    (today.opening + today.additions -tomorrow.opening) AS sold
                FROM all_stock AS today
                INNER JOIN all_stock AS tomorrow ON tomorrow.product_id = today.product_id
                    AND DATE(tomorrow.stock_date) = DATE(today.stock_date) + 1
            ),
            totals AS(
                SELECT report_date, SUM(sold*selling_price) AS total_sales, SUM(sold*purchase_price) AS total_cost
                FROM sales  
                GROUP BY report_date
            ),
            exp AS(
                SELECT date, SUM(amount) total_expenses
                FROM expenses
                WHERE shop_id = %s
                GROUP BY date
            )
            SELECT COALESCE(report_date, date), COALESCE(total_sales,0), COALESCE(total_cost,0), COALESCE(total_expenses,0) AS total_expenses
            FROM totals
            LEFT JOIN exp ON exp.date=totals.report_date   
            WHERE total_sales > 0 OR total_expenses>0
            ORDER BY report_date     
            """
            params = [current_user.shop.id, from_date, to_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            profits = []
            for datum in data:                
                profits.append(Profit(datum[0], datum[1], datum[2], datum[3]))

            return profits 
         
    def __call__(self):        
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')
        from_date = datetime.now(pytz.timezone("Africa/Nairobi")).replace(day=1).strftime('%Y-%m-%d')
        to_date = max_date
        page = 1
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                page = int(request.args.get('page', 1))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        profits = self.fetch(from_date, to_date) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(profits)==50 else 0
               
        return render_template('reports/profit-report.html', page_title='Reports > Profit & Loss', helper=Helper(), menu='reports', sub_menu='profit_report',
                               profits=profits, from_date=from_date, to_date=to_date, max_date=max_date,
                               page=page, prev_page=prev_page, next_page=next_page
                               )