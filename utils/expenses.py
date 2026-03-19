import pytz
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
            cursor.execute(
                """
                SELECT id, date, name, amount, created_by
                FROM expenses
                WHERE DATE(date) BETWEEN DATE(%s) AND DATE(%s)
                  AND shop_id = %s
                """,
                (from_date, to_date, current_user.shop.id)
            )
            rows = cursor.fetchall()

        if not rows:
            return []

        # Fetch all users once, build lookup — avoids N+1
        users_map = {u.id: u for u in SystemUsers(self.db).fetch()}

        return [
            Expense(row[0], row[1], row[2], row[3], users_map.get(row[4]))
            for row in rows
        ]
           
    def get_total(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE DATE(date) = DATE(%s) AND shop_id = %s
                """,
                (report_date, current_user.shop.id)
            )
            return cursor.fetchone()[0]
        
    def add(self, expense_date, name, amount):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO expenses(date, name, amount, shop_id, created_at, created_by)
                    VALUES(DATE(%s), %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s)
                    RETURNING id
                    """,
                    (expense_date, name.upper(), amount, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            self.db.conn.rollback()
            print(f"Error inserting expense: {e}")
            raise 
            
    def delete(self, id):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM expenses WHERE id = %s",
                    (id,)
                )
                self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            print(f"Error deleting expense: {e}")
            raise
        
    def __call__(self):
        nairobi = pytz.timezone("Africa/Nairobi")
        now = datetime.now(nairobi)
        current_date = now.strftime('%Y-%m-%d')
        from_date = now.replace(day=1).strftime('%Y-%m-%d')
        to_date = current_date

        if request.method == 'POST':
            action = request.form['action']
            if action == 'add':
                self.add(
                    request.form['expense_date'],
                    request.form['name'],
                    request.form['amount']
                )
            elif action == 'delete':
                self.delete(request.form['expense_id'])

        elif request.method == 'GET':
            from_date = request.args.get('from_date', from_date)
            to_date   = request.args.get('to_date', to_date)

        return render_template(
            'expenses.html',
            page_title='Expenses > [Do not include Purchases]',
            helper=Helper(),
            menu='expenses',
            expenses=self.fetch(from_date, to_date),
            from_date=from_date,
            to_date=to_date,
            current_date=current_date
        )