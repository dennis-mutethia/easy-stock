import hashlib, pytz
from datetime import datetime, timedelta
from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper

class Dashboard():
    def __init__(self, db): 
        self.db = db

    def _stable_color(self, text):
        """Generate a stable RGB color from a string — no flicker on refresh."""
        h = hashlib.md5(text.encode()).hexdigest()
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        # Brighten dark colors so they're visible on charts
        r, g, b = max(r, 80), max(g, 80), max(b, 80)
        return f"'rgb({r},{g},{b})'"

    def fetch_all(self, report_date):
        """Single query replacing get_total_sales, get_sales_per_item,
           get_sales_purchases_and_expenses, and get_debts."""
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            WITH all_stock AS (
                SELECT 
                    stock_date,
                    product_id,
                    CASE WHEN opening  = 'Nan' THEN 0 ELSE opening  END AS opening,
                    CASE WHEN additions = 'Nan' THEN 0 ELSE additions END AS additions,
                    purchase_price,
                    selling_price
                FROM stock
                WHERE shop_id = %s
            ),

            -- ── Per-product daily sales ──────────────────────────────────────
            sales AS (
                SELECT
                    t.stock_date,
                    t.product_id,
                    t.purchase_price,
                    t.selling_price,
                    t.additions,
                    t.opening,
                    (t.opening + t.additions - n.opening) AS sold
                FROM all_stock t
                INNER JOIN all_stock n
                    ON  n.product_id  = t.product_id
                    AND n.stock_date  = t.stock_date + INTERVAL '1 day'
            ),

            -- ── Today totals (sales / cost / purchases) ───────────────────────
            today_totals AS (
                SELECT
                    SUM(sold * selling_price)   AS total_sales,
                    SUM(sold * purchase_price)  AS total_cost,
                    SUM(additions * purchase_price) AS total_purchases
                FROM sales
                WHERE DATE(stock_date) = DATE(%s)
            ),

            -- ── Per-item sales for today (for bar/pie chart) ──────────────────
            item_sales AS (
                SELECT
                    p.name  AS item_name,
                    s.sold
                FROM sales s
                INNER JOIN products p ON p.id = s.product_id
                WHERE DATE(s.stock_date) = DATE(%s)
                  AND s.sold > 0
            ),

            -- ── 7-day trend (sales, purchases, stock, expenses) ───────────────
            weekly_totals AS (
                SELECT
                    stock_date                          AS report_date,
                    SUM(additions * purchase_price)     AS purchases,
                    SUM((opening + additions) * selling_price) AS stocks,
                    SUM(sold * selling_price)           AS sales
                FROM sales
                WHERE DATE(stock_date) BETWEEN DATE(%s) - INTERVAL '7 days' AND DATE(%s)
                GROUP BY stock_date
            ),
            weekly_exp AS (
                SELECT date, SUM(amount) AS expenses
                FROM expenses
                WHERE shop_id = %s
                GROUP BY date
            ),
            weekly AS (
                SELECT
                    w.report_date,
                    COALESCE(w.purchases, 0) AS purchases,
                    w.stocks,
                    COALESCE(w.sales, 0)     AS sales,
                    COALESCE(e.expenses, 0)  AS expenses
                FROM weekly_totals w
                LEFT JOIN weekly_exp e ON e.date = w.report_date
            ),

            -- ── Debt summary ─────────────────────────────────────────────────
            debts AS (
                SELECT
                    SUM(total - paid) AS unpaid_debts,
                    SUM(paid)         AS paid_debts
                FROM bills
                WHERE shop_id = %s
                  AND total != 'Nan'
                  AND DATE(created_at) <= DATE(%s)
            )

            -- Return all result sets tagged by type
            SELECT 
                'today'::text   AS result_type, 
                total_sales::float, 
                total_cost::float, 
                total_purchases::float, 
                NULL::text      AS label, 
                NULL::text      AS report_date, 
                NULL::float     AS expenses,
                NULL::float, 
                NULL::float, 
                NULL::float 
            FROM today_totals

            UNION ALL

            SELECT 
                'item'::text, 
                sold::float, 
                NULL::float, 
                NULL::float, 
                item_name::text, 
                NULL::text, 
                NULL::float, 
                NULL::float, 
                NULL::float, 
                NULL::float 
            FROM item_sales

            UNION ALL

            SELECT 
                'weekly'::text, 
                purchases::float, 
                stocks::float, 
                sales::float, 
                NULL::text, 
                report_date::text, 
                expenses::float, 
                NULL::float, 
                NULL::float, 
                NULL::float 
            FROM weekly

            UNION ALL

            SELECT 
                'debt'::text, 
                unpaid_debts::float, 
                paid_debts::float, 
                NULL::float, 
                NULL::text, 
                NULL::text, 
                NULL::float, 
                NULL::float, 
                NULL::float, 
                NULL::float 
            FROM debts
            """
            shop_id = current_user.shop.id
            params = (
                shop_id,        # all_stock
                report_date,    # today_totals
                report_date,    # item_sales
                report_date,    # weekly start
                report_date,    # weekly end
                shop_id,        # weekly_exp
                shop_id,        # debts
                report_date,    # debts date
            )

            cursor.execute(query, params)
            rows = cursor.fetchall()

        # ── Parse results by type tag ─────────────────────────────────────────
        total_sales = total_cost = total_purchases = 0
        items, qtys, bgcolors = [], [], []
        dates, purchases_all, stocks_all, sales_all, expenses_all = [], [], [], [], []
        unpaid_debts = paid_debts = 0

        for row in rows:
            rtype = row[0]

            if rtype == 'today':
                total_sales     = row[1] or 0
                total_cost      = row[2] or 0
                total_purchases = row[3] or 0

            elif rtype == 'item':
                name = row[4] or 'Unknown'
                items.append(f"'{name}'")
                qtys.append(row[1] or 0)
                bgcolors.append(self._stable_color(name))

            elif rtype == 'weekly':
                dates.append(f"'{row[5]}'")
                purchases_all.append(row[1] or 0)
                stocks_all.append(row[2] or 0)
                sales_all.append(row[3] or 0)
                expenses_all.append(row[6] or 0)

            elif rtype == 'debt':
                unpaid_debts = row[1] or 0
                paid_debts   = row[2] or 0

        debts    = ["'UnPaid Debts', 'Paid Debts'"]
        amounts  = [unpaid_debts, paid_debts]
        bgcolors_2 = ["'red','lime'"]

        return (
            total_sales, total_cost, total_purchases,
            items, qtys, bgcolors,
            dates, purchases_all, stocks_all, sales_all, expenses_all,
            debts, amounts, bgcolors_2
        )

    def __call__(self):
        nairobi = pytz.timezone("Africa/Nairobi")
        now = datetime.now(nairobi)
        yesterday  = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        max_date   = now.strftime('%Y-%m-%d')
        report_date = request.args.get('report_date', yesterday) if request.method == 'GET' else yesterday

        (
            total_sales, total_cost, total_purchases,
            items, qtys, bgcolors,
            dates, purchases_all, stocks_all, sales_all, expenses_all,
            debts, amounts, bgcolors_2
        ) = self.fetch_all(report_date)

        # These three still need their own queries but are self-contained utils
        from utils.expenses import Expenses
        from utils.stock.stock_take import StockTake
        from utils.customers.customer_bills import CustomerBills

        total_expenses                  = Expenses(self.db).get_total(report_date)
        total_capital, total_stock      = StockTake(self.db).get_total(report_date)
        total_unpaid_bills              = CustomerBills(self.db).get_total_unpaid_bills(report_date)

        return render_template(
            'dashboard/index.html',
            page_title='Dashboard',
            helper=Helper(),
            menu='dashboard',
            report_date=report_date,
            max_date=max_date,
            total_purchases=total_purchases if total_purchases >=0 else 0,
            total_sales=total_sales,
            total_expenses=total_expenses,
            total_capital=total_capital,
            total_stock=total_stock,
            total_cost=total_cost,
            total_unpaid_bills=total_unpaid_bills,
            items=items,
            qtys=qtys,
            bgcolors=bgcolors,
            debts=debts,
            amounts=amounts,
            bgcolors_2=bgcolors_2,
            dates=dates,
            sales=sales_all,
            expenses=expenses_all,
            stocks=stocks_all,
            purchases=purchases_all,
        )