import math
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, name, phone, user_level, shop, company, license):  
        self.id = id
        self.name = name
        self.phone = phone
        self.user_level = user_level
        self.shop = shop 
        self.company = company 
        self.license = license

class UserLevel():
    def __init__(self, id, name, level, description):
        self.id = id
        self.name = name
        self.level = level
        self.description = description 
        
class ShopType():
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description
    
class License():
    def __init__(self, id, key, package_id, expires_at, is_valid, validity):
        self.id = id
        self.key = key
        self.package_id = package_id
        self.expires_at = expires_at
        self.is_valid = is_valid
        self.validity = validity
    
class Company():
    def __init__(self, id, name, license_id):
        self.id = id
        self.name = name
        self.license_id = license_id
        
class Shop():
    def __init__(self, id, name, shop_type, company_id, location, phone_1, phone_2, paybill, account_no, till_no):
        self.id = id
        self.name = name
        self.shop_type = shop_type
        self.company_id = company_id
        self.company = None
        self.location = location
        self.phone_1 = phone_1
        self.phone_2 = phone_2
        self.paybill = paybill
        self.account_no = account_no
        self.till_no = till_no

class Package():
    def __init__(self, id, name, amount, description, color, validity, pay=None, offer=None):
        self.id = id
        self.name = name
        self.amount = amount
        self.description = description
        self.color = color
        self.validity = validity
        self.pay = pay
        self.offer = offer

class ProductCategory():
    def __init__(self, id, name, products_count):
        self.id = id
        self.name = name    
        self.products_count = products_count   

class Product():
    def __init__(self, id, name, purchase_price, selling_price, category_id):
        self.id = id
        self.name = name    
        self.purchase_price = purchase_price   
        self.selling_price = selling_price    
        self.category_id = category_id   

class Stock():
    def __init__(self, id, product_id, name, category_name, yesterday_opening, yesterday_additions, opening, additions, selling_price, purchase_price):
        self.id = id 
        self.product_id = product_id   
        self.name = name     
        self.category_name = category_name   
         # Handle None or NaN for numeric fields
        self.yesterday_opening = 0 if yesterday_opening is None or (isinstance(yesterday_opening, float) and math.isnan(yesterday_opening)) else yesterday_opening
        self.yesterday_additions = 0 if yesterday_additions is None or (isinstance(yesterday_additions, float) and math.isnan(yesterday_additions)) else yesterday_additions
        self.opening = 0 if opening is None or (isinstance(opening, float) and math.isnan(opening)) else opening
        self.additions = 0 if additions is None or (isinstance(additions, float) and math.isnan(additions)) else additions
        self.selling_price = 0 if selling_price is None or (isinstance(selling_price, float) and math.isnan(selling_price)) else selling_price
        self.purchase_price = 0 if purchase_price is None or (isinstance(purchase_price, float) and math.isnan(purchase_price)) else purchase_price

class Customer():
    def __init__(self, id, name, phone):
        self.id = id    
        self.name = name     
        self.phone = phone    

class BillEntry():
    def __init__(self, id, bill_id, stock_id, item_name, price, qty):
        self.id = id    
        self.bill_id = bill_id     
        self.stock_id = stock_id   
        self.item_name = item_name     
        self.price = price   
        self.qty = qty 
          
class PaymentMode():
    def __init__(self, id, name):
        self.id = id    
        self.name = name     
          
class Payment():
    def __init__(self, id, bill_id, amount, created_at, user, payment_mode ):
        self.id = id    
        self.bill_id = bill_id   
        self.amount = amount     
        self.created_at = created_at   
        self.user = user   
        self.payment_mode = payment_mode   
          
class Bill():
    def __init__(self, id, total, paid, created_at, customer, user, payments):
        self.id = id    
        self.total = total     
        self.paid = paid     
        self.created_at = created_at  
        self.customer = customer    
        self.user = user   
        self.payments = payments
        self.cash = 0 
        self.mpesa = 0
        for payment in payments:
            if payment.payment_mode.name == 'CASH':
                self.cash = self.cash + payment.amount
            elif payment.payment_mode.name == 'MPESA':
                self.mpesa = self.mpesa + payment.amount
         
class Expense():
    def __init__(self, id, date, name, amount, user):
        self.id = id    
        self.date = date  
        self.name = name 
        self.amount = amount     
        self.user = user   
         
class Sale():
    def __init__(self, report_date, item_name, category_name, selling_price, sold):
        self.report_date = report_date
        self.item_name = item_name  
        self.category_name = category_name 
        self.selling_price = selling_price     
        self.sold = sold   
         
class Purchase():
    def __init__(self, report_date, name, category_name, purchase_price, additions):
        self.report_date = report_date
        self.name = name  
        self.category_name = category_name 
        self.purchase_price = purchase_price     
        self.additions = additions    
         
class Profit():
    def __init__(self, report_date, sales, cost, expenses):
        self.report_date = report_date
        self.sales = sales  
        self.cost = cost    
        self.expenses = expenses   
        self.gross_profit = sales - cost
        self.net_profit = sales - cost - expenses
         
class Statement():
    def __init__(self, date, sales, purchases, expenses):
        self.date = date
        self.sales = sales  
        self.purchases = purchases    
        self.expenses = expenses   
        
        
          
        
        