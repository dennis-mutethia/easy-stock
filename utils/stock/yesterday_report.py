from datetime import datetime
from flask import render_template, request

from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories
from utils.stock.stock_take import StockTake

class YesterdayStockReport():
    def __init__(self, db): 
        self.db = db
        self.stock_take = StockTake(db)
      
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
             
        product_categories = ProductsCategories(self.db).fetch()
        stocks = self.stock_take.fetch(stock_date, search, category_id)
        return render_template('stock/yesterday-stock-report.html', helper=Helper(), 
                               product_categories=product_categories, stocks=stocks, 
                               page_title='Stock Report', stock_date=stock_date, current_date=current_date, search=search, category_id=category_id)
