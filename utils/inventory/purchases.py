from flask import render_template, request
from datetime import datetime

from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories
from utils.stock.stock_take import StockTake

class Purchases():
    def __init__(self, db): 
        self.db = db 
        
    def __call__(self):
        search = ''
        category_id = 0   
        current_date = datetime.now().strftime('%Y-%m-%d')
        stock_date = current_date   
        if request.method == 'GET':   
            try:    
                search = request.args.get('search', '')
                category_id = int(request.args.get('category_id', 0))
                stock_date = request.args.get('stock_date', default=current_date)
            except ValueError as e:
                print(f"Error converting category_id: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
        
        if request.method == 'POST':       
            if request.form['action'] == 'update':
                id = request.form['id']
                opening = request.form['opening']
                additions = request.form['additions']     
                StockTake(self.db).update(id, opening, additions)
                return 'success'
        
        product_categories = ProductsCategories(self.db).fetch()
        stocks = StockTake(self.db).fetch(stock_date, search, category_id)
        return render_template('inventory/purchases.html', helper=Helper(), 
                               product_categories=product_categories, stocks=stocks, 
                               page_title='Purchases', stock_date=stock_date, current_date=current_date, search=search, category_id=category_id)
