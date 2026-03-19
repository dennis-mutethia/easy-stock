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
        nairobi = pytz.timezone("Africa/Nairobi")
        max_date    = (datetime.now(nairobi) - timedelta(days=1)).strftime('%Y-%m-%d')
        report_date = max_date
        category_id = 0

        if request.method == 'GET':
            try:
                report_date = request.args.get('report_date', max_date)
                category_id = int(request.args.get('category_id', 0))
            except ValueError as e:
                print(f"Error parsing query params: {e}")

        stocks      = self.stock_report.fetch(report_date, category_id)
        grand_total = sum(s.selling_price * s.sold for s in stocks)

        return render_template(
            'reports/stock-report.html',
            page_title='Reports > Stock',
            helper=Helper(),
            menu='stock',
            sub_menu='stock_report',
            stocks=stocks,
            grand_total=grand_total,
            product_categories=ProductsCategories(self.db).fetch(),
            category_id=category_id,
            max_date=max_date,
            report_date=report_date
        )