import pytz
from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Purchase
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

class PurchasesReport():
    def __init__(self, db): 
        self.db = db

    def fetch(self, report_date, category_id=0):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """      
            WITH products AS (
                SELECT id, name, category_id
                FROM products 
                WHERE shop_id = %s
            )
            
            SELECT s.stock_date, p.name, pc.name AS category_name, s.purchase_price, additions 
            FROM stock s
            INNER JOIN products p ON p.id = s.product_id
            LEFT JOIN product_categories pc ON pc.id= s.category_id   
            WHERE DATE(s.stock_date) = DATE(%s) AND s.shop_id = %s AND s.additions IS NOT NULL AND s.additions>0
            """
            params = [current_user.shop.id, report_date, current_user.shop.id]
            
            if category_id > 0:
                query = query + " AND p.category_id = %s "
                params.append(category_id)
            
            query = query + """
            ORDER BY pc.name, p.name
            """
                        
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            purchases = []
            for datum in data:                       
                purchases.append(Purchase(datum[0], datum[1], datum[2], datum[3], datum[4]))

            return purchases 
         
    def __call__(self):
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        from_date = to_date = current_date
        category_id = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                category_id = int(request.args.get('category_id', 0))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        purchases = self.fetch(from_date, category_id) 
        grand_total =  0
        for purchase in purchases:
            total = purchase.purchase_price * purchase.additions
            grand_total = grand_total + total
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/purchases-report.html', page_title='Reports > Purchases', helper=Helper(), menu='reports', sub_menu='purchases_report',
                               purchases=purchases, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               current_date=current_date, from_date=from_date, to_date=to_date
                            )