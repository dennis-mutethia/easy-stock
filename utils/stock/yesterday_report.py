import pytz
from datetime import datetime, timedelta
from flask import render_template, request

from utils.helper import Helper
from utils.inventory.products_categories import ProductsCategories
from utils.reports.stock_report import StockReport

class YesterdayStockReport():
    def __init__(self, db): 
        self.db = db
        self.stock_report = StockReport(db)    
    
    def __call__(self):
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')
        report_date = max_date
        category_id = 0
        
        if request.method == 'GET':   
            try:    
                report_date = request.args.get('report_date', report_date)
                category_id = int(request.args.get('category_id', 0))
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        stocks = self.stock_report.fetch(report_date, category_id) 
        grand_total =  0
        for stock in stocks:
            total = stock.selling_price * stock.sold
            grand_total = grand_total + total
        
        product_categories = ProductsCategories(self.db).fetch()
        return render_template('reports/stock-report.html', page_title='Reports > Stock', helper=Helper(), menu='stock', sub_menu='stock_report',
                               stocks=stocks, grand_total=grand_total, product_categories=product_categories, category_id=category_id,
                               max_date=max_date, report_date=report_date)