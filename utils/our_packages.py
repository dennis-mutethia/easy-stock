import time
from flask import jsonify, render_template, request
from flask_login import current_user

from utils.entities import Package
from utils.helper import Helper
from utils.paystack import Charge, Transactions

class OurPackages():
    def __init__(self, db): 
        self.db = db
    
    def fetch_packages(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT id, name, amount, description, color, validity, pay, offer
            FROM packages 
            ORDER BY validity
            """
                        
            cursor.execute(query)
            data = cursor.fetchall()
            packages = []
            for datum in data:   
                packages.append(Package(datum[0], datum[1], datum[2], datum[3], datum[4], datum[5], datum[6], datum[7]))

            return packages 
        
    def pay(self, phone, amount, license_id, package_id):
        charge_details = Charge().stk_push(phone, amount)
        if charge_details.get('status'):
            reference = charge_details.get('data').get('reference')
            
            while True:            
                transaction_details = Transactions().verify(reference=reference)
                if transaction_details and transaction_details.get('status'):
                    status = transaction_details.get('data').get('status')
                    
                    if status == 'success':
                        Helper(self.db).update_license(license_id, package_id)
                        return True
                    elif status == 'failed':
                        return False 
                
        return False            
          
    def __call__(self):    
        if request.method == 'POST':  
            if request.form['action'] == 'pay':
                phone = request.form['phone']
                amount = int(request.form['amount'])
                license_id = request.form['license_id']
                package_id = request.form['package_id']
                is_paid = self.pay(phone, amount, license_id, package_id)   
                return jsonify({
                    "success": is_paid
                }), 200                
                
        toastr_message = None   
        package_id = current_user.license.package_id
        package = self.db.get_package_by_id(package_id)  
        packages = self.fetch_packages()
            
        return render_template('packages.html', page_title='Our Packages', helper=Helper(),
                               package = package, packages = packages, toastr_message = toastr_message)