from datetime import datetime
from flask import render_template, request
from flask_login import current_user

from utils.entities import Purchase
from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories

class PurchasesReport():
    def __init__(self, db): 
        self.db = db

    def fetch(self, report_date, category_id=0, page=0):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT s.stock_date, s.name, pc.name AS category_name, s.purchase_price, additions 
            FROM stock s
            LEFT JOIN product_categories pc ON pc.id= s.category_id   
            WHERE DATE(s.stock_date) = DATE(%s) AND s.shop_id = %s AND s.additions IS NOT NULL AND s.additions>0
            """
            params = [report_date, current_user.shop.id]
            
            if category_id > 0:
                query = query + " AND s.category_id = %s "
                params.append(category_id)
            
            query = query + """
            ORDER BY pc.name, s.name
            """
            
            if page>0:
                query = query + """
                LIMIT 50 OFFSET %s
                """
                params.append((page - 1)*50)
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            purchases = []
            for datum in data:                       
                purchases.append(Purchase(datum[0], datum[1], datum[2], datum[3], datum[4]))

            return purchases 
         
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = to_date = current_date
        page = 1
        category_id = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                category_id = int(request.args.get('category_id', 0))
                page = int(request.args.get('page', 1))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        purchases = self.fetch(from_date, category_id, page) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(purchases)==50 else 0
        grand_total =  0
        for purchase in purchases:
            total = purchase.purchase_price * purchase.additions
            grand_total = grand_total + total
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/purchases-report.html', page_title='Reports > Purchases', helper=Helper(),
                               purchases=purchases, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               current_date=current_date, from_date=from_date, to_date=to_date, 
                                page=page, prev_page=prev_page, next_page=next_page)