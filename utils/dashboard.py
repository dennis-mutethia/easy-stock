import random, pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.customers.customer_bills import CustomerBills
from utils.expenses import Expenses
from utils.helper import Helper
from utils.stock.stock_take import StockTake

class Dashboard():
    def __init__(self, db): 
        self.db = db
    
    
    def get_debts(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT SUM(total - paid) AS unpaid_debts, SUM(paid) AS paid_debts
            FROM bills
            WHERE shop_id = %s AND total != 'Nan' AND DATE(created_at) <= %s
            """
            params = [current_user.shop.id, report_date]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            items = []
            qtys = []
            bgcolors = []
            for datum in data:  
                items.append("'UnPaid Debts', 'Paid Debts'")
                qtys.append(datum[0] if datum[0] is not None else 0)
                qtys.append(datum[1] if datum[1] is not None else 0)
                bgcolors.append("'red','lime'")

            return items, qtys, bgcolors
    
    def get_sales_per_item(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH products AS (
                SELECT id, name
                FROM products
                WHERE shop_id = %s
            ),
            all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions
                FROM stock
                WHERE shop_id = %s
            ),
            today AS (
                SELECT 
                    product_id, 
                    name, 
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions
                FROM all_stock
                INNER JOIN products ON products.id = all_stock.product_id
                WHERE DATE(stock_date) = DATE(%s)
            ),
            tomorrow AS (
                SELECT 
                    product_id, 
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening
                FROM all_stock
                WHERE DATE(stock_date) = DATE(%s) + 1
            ),
            source AS(
                SELECT today.name AS item_name, (today.opening + today.additions - tomorrow.opening) AS sold
                FROM today
                INNER JOIN tomorrow ON tomorrow.product_id = today.product_id
            )        
            SELECT item_name, sold
            FROM source 
            WHERE sold > 0         
            """
            params = [current_user.shop.id, current_user.shop.id, report_date, report_date]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            items = []
            qtys = []
            bgcolors = []
            for datum in data:  
                items.append(f"'{datum[0] if datum[0] is not None else 0}'")
                qtys.append(datum[1] if datum[1] is not None else 0)
                bgcolors.append(f"'rgb({random.randint(1, 255)},{random.randint(1, 255)},{random.randint(1, 255)})'")

            return items, qtys, bgcolors
    
    def get_total_sales(self, report_date):
        self.db.ensure_connection()
        total_sales = 0 
        total_cost = 0
        total_purchases = 0
        with self.db.conn.cursor() as cursor:
            query = """                       
            WITH all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions,
                    purchase_price,
                    selling_price
                FROM stock
                WHERE shop_id = %s
            ),
            sales AS(
                SELECT 
                    today.purchase_price,
                    today.selling_price,
                    today.additions,
                    (today.opening + today.additions - tomorrow.opening) AS sold
                FROM all_stock AS today
                INNER JOIN all_stock AS tomorrow ON tomorrow.product_id = today.product_id
                    AND DATE(tomorrow.stock_date) = DATE(today.stock_date) + 1
                WHERE DATE(today.stock_date) = DATE(%s)
            ),
            totals AS(
                SELECT SUM(sold*selling_price) AS total_sales, SUM(sold*purchase_price) AS total_cost, SUM(additions*purchase_price) AS total_purchases
                FROM sales  
            )
            SELECT total_sales, total_cost, total_purchases
            FROM totals
            """
            params = [current_user.shop.id, report_date]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            for datum in data:   
                total_sales = datum[0]   
                total_cost = datum[1]  
                total_purchases = datum[2]        

            return total_sales, total_cost, total_purchases 
        
    def get_sales_purchases_and_expenses(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """                                  
            WITH all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions,
                    purchase_price,
                    selling_price
                FROM stock
                WHERE shop_id = %s
            ),
            sales AS(
                SELECT 
                    today.stock_date,
                    today.opening,
                    today.additions,
                    today.purchase_price,
                    today.selling_price,
                    (today.opening + today.additions - tomorrow.opening) AS sold
                FROM all_stock AS today
                INNER JOIN all_stock AS tomorrow ON tomorrow.product_id = today.product_id
                    AND DATE(tomorrow.stock_date) = DATE(today.stock_date) + 1
            ),
            totals AS(
                SELECT 
                    stock_date AS report_date,
                    SUM(additions*purchase_price) AS purchases,
                    SUM((opening+additions)*selling_price) AS stocks,
                    SUM(sold*selling_price) AS sales
                FROM sales  
                WHERE DATE(stock_date) BETWEEN DATE(%s) - INTERVAL '7 days' AND DATE(%s)
                GROUP BY stock_date
            ),
            exp AS(
                SELECT date, SUM(amount) expenses
                FROM expenses
                WHERE shop_id = %s
                GROUP BY date
            )
            SELECT report_date, COALESCE(purchases,0) AS purchases, stocks, COALESCE(sales,0) AS sales, COALESCE(expenses,0) AS expenses
            FROM totals
            LEFT JOIN exp ON exp.date=totals.report_date         
            """
            params = [current_user.shop.id, report_date, report_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            dates = []
            purchases_all = []
            stocks_all = []
            sales_all = []
            expenses_all = []
            for datum in data:  
                dates.append(f"'{datum[0]}'")
                purchases_all.append(datum[1] if datum[1] is not None else 0)
                stocks_all.append(datum[2] if datum[2] is not None else 0)
                sales_all.append(datum[3] if datum[3] is not None else 0)
                expenses_all.append(datum[4] if datum[4] is not None else 0)

            return dates, purchases_all, stocks_all, sales_all, expenses_all
                
    def __call__(self):
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        report_date = yesterday.strftime('%Y-%m-%d')
        max_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', report_date)
                
            except Exception as e:
                print(f"An error occurred: {e}")
        
        total_sales, total_cost, total_purchases = self.get_total_sales(report_date)
        total_expenses = Expenses(self.db).get_total(report_date)
        total_capital, total_stock = StockTake(self.db).get_total(report_date)
        total_unpaid_bills = CustomerBills(self.db).get_total_unpaid_bills(report_date)
        items, qtys, bgcolors = self.get_sales_per_item(report_date)
        debts, amounts, bgcolors_2 = self.get_debts(report_date)
        dates, purchases, stocks, sales, expenses = self.get_sales_purchases_and_expenses(report_date)
         
        return render_template('dashboard/index.html', page_title='Dashboard', helper=Helper(), menu = 'dashboard',
                               report_date=report_date, max_date=max_date,
                               total_purchases=total_purchases, total_sales=total_sales, total_expenses=total_expenses,
                               total_capital=total_capital, total_stock=total_stock, total_cost=total_cost, total_unpaid_bills=total_unpaid_bills,
                               items=items, qtys=qtys, bgcolors=bgcolors, debts=debts, amounts=amounts, bgcolors_2=bgcolors_2,
                               dates=dates, sales=sales, expenses=expenses, stocks=stocks, purchases=purchases
                               )