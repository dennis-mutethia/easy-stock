import random
from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.expenses import Expenses
from utils.helper import Helper
from utils.stock.stock_take import StockTake
from utils.pos.bill_entries import BillEntries
from utils.pos.bills import Bills

class Dashboard():
    def __init__(self, db): 
        self.db = db
    
    def get_sales_per_item(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT item_name, SUM(qty) sold
            FROM bill_entries 
            WHERE DATE(created_at) = DATE(%s) AND shop_id = %s
            AND bill_id>0 AND qty>0
            GROUP BY item_name            
            """
            params = [report_date, current_user.shop.id]
            
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
    
    def get_sales_and_expenses(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH exp AS(
                SELECT date, SUM(amount) total_expenses
                FROM expenses
                GROUP BY date
            ),
            sales AS(
                SELECT DATE(created_at) AS report_date, SUM(total) AS total_sales
                FROM bills
                WHERE DATE(created_at) BETWEEN DATE(%s) - INTERVAL '30 days' AND DATE(%s) AND shop_id=%s AND total != 'Nan'
                GROUP BY report_date
            )
            SELECT report_date, total_sales, COALESCE(total_expenses,0) AS total_expenses
            FROM sales
            LEFT JOIN exp ON exp.date=sales.report_date         
            """
            params = [report_date, report_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            dates = []
            sales_all = []
            expenses_all = []
            for datum in data:  
                dates.append(f"'{datum[0]}'")
                sales_all.append(datum[1] if datum[1] is not None else 0)
                expenses_all.append(datum[2] if datum[2] is not None else 0)

            return dates, sales_all, expenses_all
          
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
        current_date = datetime.now().strftime('%Y-%m-%d')
        report_date = current_date
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', current_date)
                
            except Exception as e:
                print(f"An error occurred: {e}")
        
        total_cost, total_sales = BillEntries(self.db).get_total(report_date)
        total_expenses = Expenses(self.db).get_total(report_date)
        total_capital, total_stock = StockTake(self.db).get_total(report_date)
        total_unpaid_bills = Bills(self.db).get_total_unpaid_bills()
        items, qtys, bgcolors = self.get_sales_per_item(report_date)
        dates, sales_all, expenses_all = self.get_sales_and_expenses(report_date)
        dates_2, stocks_2, purchases = self.get_stock_trend(report_date)
         
        return render_template('dashboard/index.html', page_title='Dashboard', helper=Helper(),
                               report_date=report_date,
                               total_cost=total_cost, total_sales=total_sales, total_expenses=total_expenses,
                               total_capital=total_capital, total_stock=total_stock, total_unpaid_bills=total_unpaid_bills,
                               items=items, qtys=qtys, bgcolors=bgcolors, dates=dates, sales_all=sales_all, expenses_all=expenses_all,
                               dates_2=dates_2, stocks_2=stocks_2, purchases=purchases
                               )