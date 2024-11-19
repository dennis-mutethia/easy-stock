import os
from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, logout_user, login_required
from dotenv import load_dotenv
from flask_session import Session
from redis import Redis

from utils.account_profile import AccountProfile
from utils.our_packages import OurPackages
from utils.customers.customer_bills import CustomerBills
from utils.customers.customers import Customers
from utils.dashboard import Dashboard
from utils.db import Db
from utils.expenses import Expenses
from utils.inventory.products import Products
from utils.inventory.products_categories import ProductsCategories
from utils.inventory.purchases import Purchases
from utils.inventory.stock_adjustment import StockAdjustment
from utils.stock.stock_take import StockTake
from utils.login import Login
from utils.pos.bill_details import BillDetails
from utils.pos.bill_entries import BillEntries
from utils.pos.bills import Bills
from utils.pos.new_sale import NewSale
from utils.pos.print import Print
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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis(
    host=os.getenv('REDIS_HOSTNAME'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD'),
    ssl=False if os.getenv('REDIS_SSL') in ['False', '0'] else True
)

app.config['SESSION_COOKIE_SECURE'] = True  # Set to True if using HTTPS on Vercel
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

Session(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = Db()
#db.create_base_tables()
         
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
    logout_user()
    return redirect(url_for('login'))

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

if __name__ == '__main__':
    debug_mode = os.getenv('IS_DEBUG', 'False').lower() in ['true', '1', 't']
    app.run(debug=debug_mode)
