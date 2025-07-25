import pytz, random
from datetime import datetime
from flask import redirect, render_template, request, url_for
from flask_login import login_user

from daily_stock_loader import DailyStockLoader
from utils.settings.my_shops import MyShops
from utils.settings.system_users import SystemUsers

class Login():
    def __init__(self, db): 
        self.db = db        
     
    def login(self):  
        phone = request.form['phone']
        password = request.form['password']   
        user = SystemUsers(self.db).authenticate(phone, password)
        
        if user:        
            login_user(user)
            if user.user_level.id in [0, 1]:               
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('stockTake')) 
        else: 
            error = 'Login failed! Phone & Password do not match or Phone does not exist.'
            shop_types = MyShops(self.db).fetch_shop_types()
            return render_template('login.html', shop_types=shop_types, error=error)
    
    def register(self):           
        company_name = request.form['company_name']
        shop_name = request.form['shop_name']  
        shop_type_id = request.form['shop_type_id']
        shop_location = request.form['shop_location'] 
        user_name = request.form['user_name']    
        user_phone = request.form['user_phone']
        user_password = request.form['user_password'] 
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')
        
        package = self.db.get_package_by_id(1)
        payment_id = self.db.save_payment(0, 0, 4)
        license_id = self.db.save_license(package, payment_id)
        company_id = self.db.save_company(company_name, license_id)
        shop_id = MyShops(self.db).add(shop_name, shop_type_id, company_id, shop_location, created_by=0)
        user = SystemUsers(self.db).get_by_phone(user_phone)
        if user is None:
            user_id = SystemUsers(self.db).add(user_name, user_phone, 1, shop_id, user_password)
            user = SystemUsers(self.db).get_by_id(user_id)
        else:
            SystemUsers(self.db).update(user_id, user_name, user_phone, 1, shop_id, password=user_password)
                    
        login_user(user)
        self.db.import_product_categories_template_data(shop_id, shop_type_id)
        self.db.import_products_template_data(shop_id, shop_type_id)
        DailyStockLoader().load(current_date, register=True) 
        return redirect(url_for('dashboard'))         
    
    def reset_password(self):
        phone = request.form['phone']
        password = str(random.randint(1000, 9999))
        print(password)
        ## send SMS
        SystemUsers(self.db).reset_password(phone, password, 0)
        shop_types = MyShops(self.db).fetch_shop_types()
        return render_template('login.html', shop=None, shop_types=shop_types, error=None)
     
    def __call__(self):
        if request.method == 'POST':
            if request.form['action'] == 'register':
                return self.register()
            elif request.form['action'] == 'login':
                return self.login()
            elif request.form['action'] == 'reset_password':
                return self.reset_password()

        shop_types = MyShops(self.db).fetch_shop_types()
        return render_template('login.html', shop=None, shop_types=shop_types, error=None)
