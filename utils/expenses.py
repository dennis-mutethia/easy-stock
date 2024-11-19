from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Expense
from utils.helper import Helper
from utils.settings.system_users import SystemUsers

class Expenses():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self, from_date, to_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, date, name, amount, created_by
            FROM expenses
            WHERE (DATE(date) BETWEEN DATE(%s) AND DATE(%s)) AND shop_id = %s
            """
            params = [from_date, to_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            expenses = []
            for datum in data:                
                user = SystemUsers(self.db).get_by_id(datum[4])       
                expenses.append(Expense(datum[0], datum[1], datum[2], datum[3], user))

            return expenses 
           
    def get_total(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT SUM(amount)
            FROM expenses
            WHERE DATE(date) = DATE(%s) AND shop_id = %s
            """
            params = [report_date, current_user.shop.id]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchone()
            if data:
                return int(data[0]) if data[0] is not None and isinstance(data[0], (int, float)) else 0
            else:
                return None
        
    def add(self, name, amount):
        self.db.ensure_connection()            
        query = """
        INSERT INTO expenses(date, name, amount, shop_id, created_at, created_by) 
        VALUES(CURRENT_DATE, %s, %s, %s, NOW(), %s)
        RETURNING id
        """

        params = (name.upper(), amount, current_user.shop.id, current_user.id)
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
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
            DELETE FROM expenses
            WHERE id=%s
            """
            cursor.execute(query, (id,))
            self.db.conn.commit()
        
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        to_date = current_date
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                
            except Exception as e:
                print(f"An error occurred: {e}")
                
        if request.method == 'POST':       
            if request.form['action'] == 'add':
                name = request.form['name']
                amount = request.form['amount']                
                self.add(name, amount)                     
                
            elif request.form['action'] == 'delete':
                expense_id = request.form['expense_id']
                self.delete(expense_id)
                
                
        expenses = self.fetch(from_date, to_date) 
            
        return render_template('expenses.html', page_title='Expenses > [Do not include Purchases]', helper=Helper(),
                               expenses=expenses, from_date=from_date, to_date=to_date, current_date=current_date )