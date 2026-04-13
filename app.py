import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, make_response, redirect, render_template, url_for, send_from_directory
from flask_login import LoginManager, logout_user, login_required
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, set_access_cookies, unset_jwt_cookies

from utils.account_profile import AccountProfile
from utils.cashbox import CashBox
from utils.our_packages import OurPackages
from utils.customers.customer_bills import CustomerBills
from utils.customers.customers import Customers
from utils.customers.loyalty_points import LoyaltyPoints
from utils.dashboard import Dashboard
from utils.db import Db
from utils.expenses import Expenses
from utils.inventory.products import Products
from utils.inventory.products_categories import ProductsCategories
from utils.inventory.purchases import Purchases
from utils.inventory.stock_adjustment import StockAdjustment
from utils.stock.stock_take import StockTake
from utils.login import Login
from utils.reports.bills_report import BillsReport
from utils.reports.expenses_report import ExpensesReport
from utils.reports.profit_report import ProfitReport
from utils.reports.purchases_report import PurchasesReport
from utils.reports.sales_report import SalesReport
from utils.reports.statement_of_account import StatementOfAccount
from utils.reports.stock_report import StockReport
from utils.settings.companies import Companies
from utils.settings.company_shops import CompanyShops
from utils.settings.my_shops import MyShops
from utils.settings.system_users import SystemUsers
from utils.stock.yesterday_report import YesterdayStockReport

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # One year in seconds

# Load environment variables from .env file
load_dotenv()
# JWT Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY'))
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = True          # HTTPS only (Vercel uses HTTPS)
app.config['JWT_COOKIE_HTTPONLY'] = True         # No JS access to cookie
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_COOKIE_CSRF_PROTECT'] = True     # CSRF protection for cookie-based JWT
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)

jwt = JWTManager(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.after_request
def refresh_token_if_expiring_soon(response):
    try:
        jwt_data = get_jwt()
        exp_timestamp = jwt_data.get("exp")
        if not exp_timestamp:
            return response

        now = datetime.now(timezone.utc)
        expire_time = datetime.fromtimestamp(exp_timestamp, timezone.utc)
        time_remaining = expire_time - now

        if time_remaining < timedelta(minutes=10):
            identity = get_jwt_identity()
            new_token = create_access_token(identity=identity)
            set_access_cookies(response, new_token)

    except (RuntimeError, KeyError):
        pass

    return response

db = Db()
#db.migration()
         
# Callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return SystemUsers(db).get_by_id(user_id)

# Routes
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return Login(db)()

@app.route('/logout')
@login_required
def logout():
    response = make_response(redirect(url_for('login')))
    unset_jwt_cookies(response)   # clears both access + refresh cookies
    logout_user()
    return response

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard(): 
    return Dashboard(db)() 

@app.route('/inventory-products-categories', methods=['GET', 'POST'])
@login_required
def inventoryProductsCategories():
    return ProductsCategories(db)()

@app.route('/inventory-products-categories-update', methods=['POST'])
@login_required
def inventoryProductsCategoriesUpdate():    
    return ProductsCategories(db)()

@app.route('/inventory-products', methods=['GET', 'POST'])
@login_required
def inventoryProducts():
    return Products(db)()

@app.route('/inventory-products-update', methods=['POST'])
@login_required
def inventoryProductsUpdate():    
    return Products(db)()

@app.route('/stock-take', methods=['GET', 'POST'])
@login_required
def stockTake():
    return StockTake(db)()

@app.route('/stock-take-update', methods=['POST'])
@login_required
def stockTakeUpdate():    
    return StockTake(db)()

@app.route('/yesterday-stock-report', methods=['GET'])
@login_required
def yesterdayStockReport():    
    return YesterdayStockReport(db)()

@app.route('/inventory-purchases', methods=['GET', 'POST'])
@login_required
def inventoryPurchases():
    return Purchases(db)()

@app.route('/inventory-purchases-update', methods=['POST'])
@login_required
def inventoryPurchasesUpdate():
    return Purchases(db)()

@app.route('/inventory-stock-adjustment', methods=['GET', 'POST'])
@login_required
def inventoryStockAdjustment():
    return StockAdjustment(db)()

@app.route('/inventory-stock-adjustment-update', methods=['POST'])
@login_required
def inventoryStockAdjustmentUpdate():
    return StockAdjustment(db)()

@app.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    return Customers(db)()

@app.route('/loyalty-points', methods=['GET', 'POST'])
@login_required
def loyaltyPoints():
    return LoyaltyPoints(db)()

@app.route('/customer-update', methods=['POST'])
@login_required
def customerUpdate():
    return Customers(db)()

@app.route('/customer-bills', methods=['GET', 'POST'])
@login_required
def customerBills():
    return CustomerBills(db)()

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    return Expenses(db)()

@app.route('/cashbox', methods=['GET', 'POST'])
@login_required
def cashbox():
    return CashBox(db)()

@app.route('/bills-report', methods=['GET'])
@login_required
def billsReport():
    return BillsReport(db)()

@app.route('/sales-report', methods=['GET'])
@login_required
def salesReport():
    return SalesReport(db)()

@app.route('/purchases-report', methods=['GET'])
@login_required
def purchasesReport():
    return PurchasesReport(db)()

@app.route('/expenses-report', methods=['GET'])
@login_required
def expensesReport():
    return ExpensesReport(db)()

@app.route('/profit-and-loss-report', methods=['GET'])
@login_required
def profitReport():
    return ProfitReport(db)()

@app.route('/statement-of-account', methods=['GET'])
@login_required
def statementOfAccount():
    return StatementOfAccount(db)()

@app.route('/stock-report', methods=['GET'])
@login_required
def stockReport():
    return StockReport(db)()

@app.route('/my-shops', methods=['GET', 'POST'])
@login_required
def myShops():
    return MyShops(db)()

@app.route('/system-users', methods=['GET', 'POST'])
@login_required
def systemUsers():
    return SystemUsers(db)()

@app.route('/system-users-update', methods=['POST'])
@login_required
def systemUserUpdate():
    return SystemUsers(db)()

@app.route('/companies', methods=['GET', 'POST'])
@login_required
def companies():
    return Companies(db)()

@app.route('/company-shops', methods=['GET'])
@login_required
def companyShops():
    return CompanyShops(db)()

@app.route('/account-profile', methods=['GET', 'POST'])
@login_required
def accountProfile():
    return AccountProfile(db)()

@app.route('/packages', methods=['GET', 'POST'])
@login_required
def ourPackages():
    return OurPackages(db)()

@app.route('/download', methods=['GET'])
@login_required
def download():
    return render_template('download.html', page_title='Download > Android App')

@app.route('/download/android', methods=['GET'])
def download_android():
    return send_from_directory('static/bundles', 'EasyStock.apk', as_attachment=True)

if __name__ == '__main__':
    debug_mode = os.getenv('IS_DEBUG', False) in ['True', '1', 't']
    app_port = int(os.getenv('APP_PORT', 5000))
    if debug_mode:
        app.run(debug=debug_mode, port=app_port)
    else:
        app.run()
