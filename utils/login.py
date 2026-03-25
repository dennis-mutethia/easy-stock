import random, pytz
from datetime import datetime
from flask import make_response, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies
from flask_login import login_user

from daily_stock_loader import DailyStockLoader
from utils.settings.my_shops import MyShops
from utils.settings.system_users import SystemUsers

class Login():
    def __init__(self, db): 
        self.db = db    

    def _redirect_with_jwt(self, user, endpoint):
        access_token  = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        response = make_response(redirect(url_for(endpoint)))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response
     
    def login(self):  
        phone    = request.form['phone']
        password = request.form['password']
        user     = SystemUsers(self.db).authenticate(phone, password)
        
        if user:        
            login_user(user)
            endpoint = 'dashboard' if user.user_level.id in [0, 1] else 'stockTake'
            return self._redirect_with_jwt(user, endpoint)

        shop_types = MyShops(self.db).fetch_shop_types()
        return render_template('login.html', shop_types=shop_types,
                               error='Login failed! Phone & Password do not match or Phone does not exist.')
    
    def register(self):
        form         = request.form
        current_date = datetime.now(pytz.timezone("Africa/Nairobi")).strftime('%Y-%m-%d')

        # ── Create company structure ──────────────────────────────────────────
        package    = self.db.get_package_by_id(1)
        payment_id = self.db.save_payment(0, 0, 4)
        license_id = self.db.save_license(package, payment_id)
        company_id = self.db.save_company(form['company_name'], license_id)
        shop_id    = MyShops(self.db).add(
                        form['shop_name'], form['shop_type_id'],
                        company_id, form['shop_location'], created_by=0
                     )

        # ── Create or update user ─────────────────────────────────────────────
        system_users = SystemUsers(self.db)
        user = system_users.get_by_phone(form['user_phone'])

        if user is None:
            user_id = system_users.add(form['user_name'], form['user_phone'], 1, shop_id, form['user_password'])
            user    = system_users.get_by_id(user_id)
        else:
            # BUG FIX: was referencing user_id before assignment when user already existed
            system_users.update(user.id, form['user_name'], form['user_phone'], 1, shop_id, password=form['user_password'])
            user = system_users.get_by_id(user.id)

        # ── Seed shop data and load stock ─────────────────────────────────────
        login_user(user)
        self.db.import_product_categories_template_data(shop_id, form['shop_type_id'])
        self.db.import_products_template_data(shop_id, form['shop_type_id'])
        DailyStockLoader().load(current_date, shop_id=shop_id)

        return self._redirect_with_jwt(user, 'dashboard')
    
    def reset_password(self):
        phone    = request.form['phone']
        password = str(random.randint(1000, 9999))
        # TODO: replace print with SMS dispatch
        print(f"Reset password for {phone}: {password}")
        SystemUsers(self.db).reset_password(phone, password, 0)
        shop_types = MyShops(self.db).fetch_shop_types()
        return render_template('login.html', shop=None, shop_types=shop_types, error=None)
     
    def __call__(self):
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'register':
                return self.register()
            elif action == 'login':
                return self.login()
            elif action == 'reset_password':
                return self.reset_password()

        shop_types = MyShops(self.db).fetch_shop_types()
        return render_template('login.html', shop=None, shop_types=shop_types, error=None)