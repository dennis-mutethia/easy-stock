from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.entities import Customer

class Customers():
    def __init__(self, db): 
        self.db = db
               
    def fetch(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, phone
                FROM customers
                WHERE shop_id = %s
                ORDER BY name
                """,
                (current_user.shop.id,)
            )
            return [Customer(*row) for row in cursor.fetchall()]
    
    def fetch_by_id(self, id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, phone
                FROM customers
                WHERE id = %s AND shop_id = %s
                """,
                (id, current_user.shop.id)
            )
            row = cursor.fetchone()
            return Customer(*row) if row else None

    def add(self, name, phone):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO customers(name, phone, shop_id, created_at, created_by) 
                    VALUES(%s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
                    ON CONFLICT (phone, shop_id) DO UPDATE
                        SET name = EXCLUDED.name,
                            updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                            updated_by = EXCLUDED.created_by
                    RETURNING id
                    """,
                    (name.upper(), phone, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            self.db.conn.rollback()
            raise
            
    def update(self, id, name, phone):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE customers
                    SET name = %s, phone = %s,
                        updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                        updated_by = %s
                    WHERE id = %s
                    """,
                    # BUG FIX: was using current_user.shop.id as updated_by
                    (name.upper(), phone, current_user.id, id)
                )
                self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise
            
    def delete(self, id):
        """Delete customer and their bills atomically — both succeed or neither does."""
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute("DELETE FROM bills WHERE customer_id = %s", (id,))
                cursor.execute("DELETE FROM customers WHERE id = %s", (id,))
            self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise

    def __call__(self):
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                self.add(request.form['name'], request.form['phone'])
            elif action == 'edit':
                self.update(request.form['id'], request.form['name'], request.form['phone'])
            elif action == 'delete':
                self.delete(request.form['customer_id'])
        
        return render_template(
            'customers/index.html',
            helper=Helper(),
            customers=self.fetch(),
            page_title='Customers'
        )