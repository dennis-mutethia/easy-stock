from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.entities import Cards

class LoyaltyPoints():
    def __init__(self, db): 
        self.db = db
               
    def fetch(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                WITH points_earned AS (
                    SELECT card_id, SUM(points_earned) AS points
                    FROM points
                    GROUP BY card_id
                ),
                points_redeemed AS (
                    SELECT card_id, SUM(points_redeemed) AS points  
                    FROM redemptions
                    GROUP BY card_id
                )
                SELECT id, card_no, name, phone, COALESCE(points_earned.points, 0) - COALESCE(points_redeemed.points, 0) AS points
                FROM cards c
                LEFT JOIN points_earned ON points_earned.card_id = c.id
                LEFT JOIN points_redeemed ON points_redeemed.card_id = c.id
                WHERE c.shop_id = %s
                ORDER BY c.card_no ASC
                """,
                (current_user.shop.id,)
            )
            return [Cards(*row) for row in cursor.fetchall()]
        
    def add(self, card_no, name, phone):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO cards(card_no, name, phone, shop_id, created_at, created_by) 
                    VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
                    ON CONFLICT (phone, shop_id) DO UPDATE
                        SET name = EXCLUDED.name,
                            updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                            updated_by = EXCLUDED.created_by
                    RETURNING id
                    """,
                    (card_no, name.upper(), phone, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return None
        except Exception as e:
            self.db.conn.rollback()
            return 'Card number or phone already exists for another customer. Please use unique values.'
            
    def update(self, id, name, phone):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE cards
                    SET name = %s, 
                        phone = %s,
                        updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi',
                        updated_by = %s
                    WHERE id = %s
                    """,
                    (name.upper(), phone, current_user.id, id)
                )
                self.db.conn.commit()
                return None
        except Exception as e:
            self.db.conn.rollback()
            return 'Phone number already exists for another customer. Please use a unique value.'
        
    def add_points(self, card_id, amount_spent, points_earned):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO points(card_id, amount_spent, points_earned, shop_id, created_at, created_by) 
                    VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
                    """,
                    (card_id, amount_spent, points_earned, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return None
        except Exception as e:
            self.db.conn.rollback()
            return 'An error occurred while adding points. Please try again later.'
    
    def redeem_points(self, card_id, points_redeemed, amount_redeemed):
        self.db.ensure_connection()
        try:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO redemptions(card_id, points_redeemed, amount_redeemed, shop_id, created_at, created_by) 
                    VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', %s) 
                    """,
                    (card_id, points_redeemed, amount_redeemed, current_user.shop.id, current_user.id)
                )
                self.db.conn.commit()
                return None
        except Exception as e:
            self.db.conn.rollback()
            return 'An error occurred while redeeming points. Please try again later.'
            
    def __call__(self):
        errors = None
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                errors = self.add(request.form['card_no'], request.form['name'], request.form['phone'])
            elif action == 'edit':
                errors = self.update(request.form['id'], request.form['name'], request.form['phone'])
            elif action == 'add_points':
                errors = self.add_points(request.form['id'], request.form['amount_spent'], request.form['points_gained'])
            elif action == 'redeem_points':
                errors = self.redeem_points(request.form['id'], request.form['points_redeemed'], request.form['amount_redeemed'])
        
        return render_template(
            'customers/loyalty-points.html',
            helper=Helper(),
            cards=self.fetch(),
            page_title='Loyalty Points',
            errors = errors
        )