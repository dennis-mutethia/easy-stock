import pytz
from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Expense
from utils.helper import Helper
from utils.settings.system_users import SystemUsers

class ExpensesReport():
    def __init__(self, db): 
        self.db = db
    
    def fetch(self, from_date, to_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, date, name, amount, created_by
            FROM expenses
            WHERE (DATE(date) BETWEEN DATE(%s) AND DATE(%s)) AND shop_id = %s
            ORDER BY date
            """
            params = [from_date, to_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            expenses = []
            for datum in data:                
                user = SystemUsers(self.db).get_by_id(datum[4])       
                expenses.append(Expense(datum[0], datum[1], datum[2], datum[3], user))

            return expenses 
         
    def __call__(self):
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        from_date = datetime.now(pytz.timezone("Africa/Nairobi")).replace(day=1).strftime('%Y-%m-%d')
        to_date = current_date
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        expenses = self.fetch(from_date, to_date) 
                  
        return render_template('reports/expenses-report.html', page_title='Reports > Expenses', helper=Helper(), menu='reports', sub_menu='expenses_report',
                               expenses=expenses, from_date=from_date, to_date=to_date, current_date=current_date                               
                               )