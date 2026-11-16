import pytz
from datetime import datetime, timedelta
from flask import render_template, request, Response
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
                    CASE WHEN opening = 'Nan' THEN 0 ELSE opening END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions, 
                    purchase_price,
                    selling_price
                FROM stock
                WHERE shop_id = %s AND DATE(stock_date) BETWEEN DATE(%s) AND DATE(%s) + 1
            ),
            sales AS(
                SELECT 
                    today.stock_date AS date, 
                    today.selling_price,
                    (today.opening + today.additions -tomorrow.opening) AS sold
                FROM all_stock AS today
                INNER JOIN all_stock AS tomorrow ON tomorrow.product_id = today.product_id
                    AND DATE(tomorrow.stock_date) = DATE(today.stock_date) + 1
            ),
            totals AS(
                SELECT date, SUM(sold*selling_price) AS total_sales, 0 AS total_purchases, 0 AS expenses
                FROM sales  
                GROUP BY date
            ),
            purchases AS(                
                SELECT stock_date AS date, 0 AS total_sales, SUM(additions*purchase_price) AS total_purchases, 0 AS expenses
                FROM all_stock  
                GROUP BY date
            ),
            expenses AS(
                SELECT date,0 AS total_sales, 0 AS total_purchases, SUM(amount) AS expenses
                FROM expenses
                WHERE shop_id = %s AND date BETWEEN DATE(%s) AND DATE(%s)
                GROUP BY date
            ),
            final AS(
                SELECT * FROM totals
                UNION SELECT * FROM purchases
                UNION SELECT * FROM expenses
            )
            SELECT date, MAX(total_sales) AS total_sales, MAX(total_purchases) AS total_purchases, MAX(expenses) AS expenses
            FROM final
            WHERE date BETWEEN DATE(%s) AND DATE(%s)
            GROUP BY date
            ORDER BY date ASC
            """
            params = [
                current_user.shop.id, from_date, to_date,
                current_user.shop.id, from_date, to_date, from_date, to_date
            ]
            
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            statements = []
            for datum in data: 
                print(datum[0], datum[1], datum[2], datum[3])                  
                statements.append(Statement(datum[0], datum[1], datum[2], datum[3]))

            return statements 
         
    def _resolve_dates(self):
        """Same defaults as the page: this month so far, up to yesterday."""
        yesterday = datetime.now(pytz.timezone("Africa/Nairobi")) - timedelta(days=1)
        max_date = yesterday.strftime('%Y-%m-%d')

        from_date = datetime.now(pytz.timezone("Africa/Nairobi")).replace(day=1).strftime('%Y-%m-%d')
        to_date = max_date

        if request.method == 'GET':
            try:
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
            except Exception as e:
                print(f"An error occurred: {e}")
        return from_date, to_date, max_date

    def __call__(self):
        from_date, to_date, max_date = self._resolve_dates()

        statements = self.fetch(from_date, to_date)

        return render_template('reports/statement-of-account.html', page_title='Reports >Statement of Account', helper=Helper(), menu='reports', sub_menu='statement_of_account',
                               statements=statements, from_date=from_date, to_date=to_date, max_date=max_date
                               )

    def download_pdf(self):
        """Same data as the page, returned as a PDF the client can send to a bank."""
        from_date, to_date, _ = self._resolve_dates()
        try:
            datetime.strptime(from_date, '%Y-%m-%d')
            datetime.strptime(to_date, '%Y-%m-%d')
        except ValueError:
            return "Invalid date range", 400
        if from_date > to_date:
            from_date, to_date = to_date, from_date

        statements = self.fetch(from_date, to_date)

        from utils.reports.statement_pdf import build_statement_pdf
        pdf_bytes = build_statement_pdf(current_user.shop.name, from_date, to_date, statements)

        filename = f"statement-of-account_{from_date}_to_{to_date}.pdf"
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )