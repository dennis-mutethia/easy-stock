import pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.entities import Bill
from utils.helper import Helper
from utils.customers.customers import Customers
from utils.customers.payments import Payments
from utils.settings.system_users import SystemUsers

class CustomerBills():
    def __init__(self, db): 
        self.db = db  
        self.customers = Customers(self.db)
          
    def fetch(self, from_date, to_date, bill_status, customer_id=0, customers=None, payment_modes=None):
        # Mutable default args are a Python gotcha — use None and default inside
        customers      = customers or []
        payment_modes  = payment_modes or []

        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, total, paid, DATE(created_at) AS created_at, customer_id, created_by
            FROM bills
            WHERE (DATE(created_at) BETWEEN DATE(%s) AND DATE(%s)) AND shop_id = %s AND total != 'Nan'
            """
            params = [from_date, to_date, current_user.shop.id]
            
            if bill_status == 1:
                query += " AND paid>=total"
            if bill_status == 2:
                query += " AND paid<total"
            if customer_id > 0:
                query += " AND customer_id=%s"
                params.append(customer_id)
            
            query += " ORDER BY id DESC"
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()

        if not data:
            return []

        users_map         = {u.id: u for u in SystemUsers(self.db).fetch()}
        customers_map     = {c.id: c for c in customers}
        payment_modes_map = {p.id: p for p in payment_modes}
        payments_map      = {}
        for p in Payments(self.db).fetch(payment_modes_map, users_map):
            payments_map.setdefault(p.bill_id, []).append(p)

        return [
            Bill(row[0], row[1], row[2], row[3],
                 customers_map.get(row[4]),
                 users_map.get(row[5]),
                 payments_map.get(row[0], []))
            for row in data
        ]
            
    def get_bills_to_pay(self, customer_id, paid):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, total - paid AS bal
                FROM bills
                WHERE total > paid AND customer_id = %s
                ORDER BY id
                """,
                (customer_id,)
            )
            data = cursor.fetchall()

        bills = []
        for row in data:
            pay_amount = min(row[1], paid)
            if pay_amount > 0:
                bills.append({'id': row[0], 'pay_amount': pay_amount})
            paid -= pay_amount

        return bills
        
    def get_total_unpaid_bills(self, report_date):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(total - paid), 0)
                FROM bills
                WHERE shop_id = %s AND total != 'Nan' AND DATE(created_at) <= %s
                """,
                (current_user.shop.id, report_date)
            )
            return cursor.fetchone()[0]
            
    def add(self, customer_id, bill_amount, bill_date):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO bills(customer_id, total, paid, shop_id, created_at, created_by) 
                    VALUES(%s, %s, 0, %s, %s, %s)
                    RETURNING id
                    """,
                    (customer_id, bill_amount, current_user.shop.id, bill_date, current_user.id)
                )
                self.db.conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            self.db.conn.rollback()
            raise
            
    def update(self, id, customer_id, bill_amount):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE bills
                    SET customer_id = %s, total = %s,
                        updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                        updated_by = %s
                    WHERE id = %s
                    """,
                    # BUG FIX: was using current_user.shop.id as updated_by
                    (customer_id, bill_amount, current_user.id, id)
                )
                self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise
            
    def pay(self, id, paid):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE bills
                    SET paid = paid + %s,
                        updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                        updated_by = %s
                    WHERE id = %s
                    """,
                    # BUG FIX: was using current_user.shop.id as updated_by
                    (paid, current_user.id, id)
                )
                self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise
               
    def __call__(self):
        nairobi = pytz.timezone("Africa/Nairobi")
        now = datetime.now(nairobi)
        current_date = now.strftime('%Y-%m-%d')
        from_date    = (now - timedelta(days=365)).strftime('%Y-%m-%d')
        to_date      = current_date
        bill_status  = 2
        customer_id  = 0
        
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'assign_customer_bill':
                bill_id     = int(request.form['bill_id'])
                bill_amount = int(request.form['bill_amount'])
                customer_id = int(request.form['customer_id'])
                bill_date   = request.form['bill_date']
                if bill_id == 0:
                    self.add(customer_id, bill_amount, bill_date)
                else:
                    self.update(bill_id, customer_id, bill_amount)
                
            elif action == 'submit_payment':
                bill_id         = int(request.form['bill_id'])
                amount_paid     = float(request.form['amount_paid'])
                payment_mode_id = int(request.form['payment_mode_id'])
                date_paid       = request.form['date_paid']
                payments    = Payments(self.db)   
                
                if bill_id > 0:
                    payments.add(bill_id, amount_paid, payment_mode_id, date_paid)
                    self.pay(bill_id, amount_paid)
                else:
                    customer_id = int(request.args.get('customer_id', customer_id))                    
                    for bill in self.get_bills_to_pay(customer_id, amount_paid):
                        payments.add(bill['id'], bill['pay_amount'], payment_mode_id, date_paid)
                        self.pay(bill['id'], bill['pay_amount'])

            elif action == 'add_new_customer':
                self.customers.add(request.form['name'], request.form['phone'])

        elif request.method == 'GET':
            try:
                from_date   = request.args.get('from_date', from_date)
                to_date     = request.args.get('to_date', to_date)
                bill_status = int(request.args.get('bill_status', bill_status))
                customer_id = int(request.args.get('customer_id', customer_id))
            except ValueError as e:
                print(f"Error parsing query params: {e}")

        customers     = self.customers.fetch()
        payment_modes = self.db.fetch_payment_modes()
        bills         = self.fetch(from_date, to_date, bill_status, customer_id, customers, payment_modes)

        # Replace manual loop with sum() expressions
        grand_total = sum(b.total  for b in bills)
        grand_paid  = sum(b.paid   for b in bills)
        cash_total  = sum(b.cash   for b in bills)
        mpesa_total = sum(b.mpesa  for b in bills)

        return render_template(
            'customers/bills.html',
            page_title='Customer > Debts',
            helper=Helper(),
            menu='customers',
            sub_menu='customer_debts',
            customers=customers,
            payment_modes=payment_modes,
            bills=bills,
            current_date=current_date,
            bill_status=bill_status,
            from_date=from_date,
            to_date=to_date,
            customer_id=customer_id,
            grand_total=grand_total,
            grand_paid=grand_paid,
            cash_total=cash_total,
            mpesa_total=mpesa_total
        )