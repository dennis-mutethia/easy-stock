from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Statement
from utils.helper import Helper

class StatementOfAccount():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self, from_date, to_date):
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
                WHERE shop_id = %s AND DATE(stock_date) BETWEEN DATE(%s) AND DATE(%s)
            ),
            sales AS(
                SELECT 
                    yesterday.stock_date AS date, 
                    yesterday.purchase_price,
                    yesterday.selling_price,
                    (today.opening-(yesterday.opening+yesterday.additions)) AS sold,
                    yesterday.additions
                FROM all_stock AS today
                INNER JOIN all_stock AS yesterday ON yesterday.product_id = today.product_id
                    AND DATE(yesterday.stock_date) = DATE(today.stock_date) - 1
            ),
            totals AS(
                SELECT date, SUM(sold*selling_price) AS total_sales, SUM(additions*purchase_price) AS total_purchases, 0 AS expenses
                FROM sales  
                GROUP BY date
            ),
            expenses AS(
                SELECT date,0,0,SUM(amount)
                FROM expenses
                WHERE shop_id = %s AND date BETWEEN DATE(%s) AND DATE(%s)
                GROUP BY date
            ),
            final AS(
                SELECT * FROM totals
                UNION SELECT * FROM expenses
            )
            SELECT * FROM final 
            ORDER BY date ASC
            """
            params = [
                current_user.shop.id, from_date, to_date,
                current_user.shop.id, from_date, to_date
            ]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            statements = []
            for datum in data:                   
                statements.append(Statement(datum[0], datum[1], datum[2], datum[3]))

            return statements 
         
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
        
        statements = self.fetch(from_date, to_date) 
                    
        return render_template('reports/statement-of-account.html', page_title='Reports >Statement of Account', helper=Helper(),
                               statements=statements, from_date=from_date, to_date=to_date, current_date=current_date
                               )