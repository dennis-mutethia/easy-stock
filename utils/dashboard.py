import random
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.expenses import Expenses
from utils.helper import Helper
from utils.stock.stock_take import StockTake
from utils.pos.bills import Bills

class Dashboard():
    def __init__(self, db): 
        self.db = db
    
    def get_sales_per_item(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH all_stock AS (
                SELECT 
                    stock_date, 
                    product_id, 
                    name, 
                    COALESCE(stock.opening, 0) AS opening, 
                    COALESCE(stock.additions, 0) AS additions 
                FROM stock
                WHERE shop_id = %s
            ),
            today AS (
                SELECT product_id, name, opening, additions
                FROM all_stock
                WHERE DATE(stock_date) = DATE(%s)
            ),
            tomorrow AS (
                SELECT product_id, opening
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
            params = [current_user.shop.id, report_date, report_date]
            
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
                WHERE shop_id = %s
            ),
            sales AS(
                SELECT 
                    today.purchase_price,
                    today.selling_price,
                    (today.opening + today.additions - tomorrow.opening) AS sold
                FROM all_stock AS today
                INNER JOIN all_stock AS tomorrow ON tomorrow.product_id = today.product_id
                    AND DATE(tomorrow.stock_date) = DATE(today.stock_date) + 1
                WHERE DATE(today.stock_date) = DATE(%s)
            ),
            totals AS(
                SELECT SUM(sold*selling_price) AS total_sales, SUM(sold*purchase_price) AS total_cost
                FROM sales  
            )
            SELECT total_sales, total_cost
            FROM totals
            """
            params = [current_user.shop.id, report_date]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            for datum in data:   
                total_sales = datum[0]   
                total_cost = datum[1]        

            return total_sales, total_cost 
        
    def get_sales_purchases_and_expenses(self, report_date):
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
                WHERE DATE(stock_date) BETWEEN DATE(%s) - INTERVAL '30 days' AND DATE(%s)
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
          
    def get_stock_trend(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH s AS(
                SELECT DATE(created_at) AS report_date, (COALESCE(opening, 0) + COALESCE(additions, 0)) * selling_price AS stock, COALESCE(additions, 0) * purchase_price AS purchases 
                FROM stock
                WHERE DATE(created_at) BETWEEN DATE(%s) - INTERVAL '30 days' AND DATE(%s) AND shop_id=%s AND opening != 'Nan' AND additions != 'Nan'
            )
            SELECT report_date, SUM(stock) AS stock, SUM(purchases) AS purchases
            FROM s
            GROUP BY report_date        
            """
            params = [report_date, report_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            dates = []
            stocks = []
            purchases = []
            for datum in data:  
                dates.append(f"'{datum[0]}'")
                stocks.append(datum[1] if datum[1] is not None else 0)
                purchases.append(datum[2] if datum[2] is not None else 0)

            return dates, stocks, purchases
                 
    def __call__(self):
        yesterday = datetime.now() - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')
        report_date = max_date
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', report_date)
                
            except Exception as e:
                print(f"An error occurred: {e}")
        
        total_sales, total_cost = self.get_total_sales(report_date)
        total_expenses = Expenses(self.db).get_total(report_date)
        total_capital, total_stock = StockTake(self.db).get_total(report_date)
        total_unpaid_bills = Bills(self.db).get_total_unpaid_bills()
        items, qtys, bgcolors = self.get_sales_per_item(report_date)
        dates, purchases, stocks, sales, expenses = self.get_sales_purchases_and_expenses(report_date)
         
        return render_template('dashboard/index.html', page_title='Dashboard', helper=Helper(),
                               report_date=report_date, max_date=max_date,
                               total_cost=total_cost, total_sales=total_sales, total_expenses=total_expenses,
                               total_capital=total_capital, total_stock=total_stock, total_unpaid_bills=total_unpaid_bills,
                               items=items, qtys=qtys, bgcolors=bgcolors, 
                               dates=dates, sales=sales, expenses=expenses, stocks=stocks, purchases=purchases
                               )