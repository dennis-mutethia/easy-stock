from flask_login import current_user

from utils.entities import Payment

class Payments():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self, payment_modes_map, users_map):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, bill_id, amount, payment_mode_id,
                       TO_CHAR(created_at + INTERVAL '3 HOURS', 'YYYY-MM-DD HH24:MI') AS created_at,
                       created_by
                FROM payments
                WHERE shop_id = %s
                """,
                (current_user.shop.id,)
            )
            return [
                Payment(
                    row[0], row[1], row[2], row[4],
                    users_map.get(row[5]),
                    payment_modes_map.get(row[3])
                )
                for row in cursor.fetchall()
            ]
       
    def add(self, bill_id, amount, payment_mode_id, date_paid):
        self.db.ensure_connection()
        # BUG FIX: was opening two nested cursors — outer one was wasted
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO payments(bill_id, amount, payment_mode_id, created_at, shop_id, created_by) 
                    VALUES(%s, %s, %s, %s, %s, %s) 
                    RETURNING id
                    """,
                    (bill_id, amount, payment_mode_id, date_paid, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            self.db.conn.rollback()
            raise
    
    def delete(self, id):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM payments WHERE id = %s",
                    (id,)
                )
            self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise