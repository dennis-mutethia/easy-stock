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
SELECT e.id, e.date, e.name, e.amount, u.id, u.name
FROM expenses e
LEFT JOIN users u ON u.id = e.created_by
WHERE e.shop_id = %s AND e.date >= %s::date AND e.date < %s::date + INTERVAL '1 day'
ORDER BY e.date
            """
            params = [current_user.shop.id,from_date, to_date]
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            if not rows:
                return []

            # Fetch all users once, build lookup — avoids N+1
            users_map = {u.id: u for u in SystemUsers(self.db).fetch()}

            return [
                Expense(row[0], row[1], row[2], row[3], users_map.get(row[4]))
                for row in rows
            ]

         
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