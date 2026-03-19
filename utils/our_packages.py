import time
from flask import jsonify, render_template, request
from flask_login import current_user

from utils.entities import Package
from utils.helper import Helper
from utils.paystack import Charge, Transactions

MAX_POLL_ATTEMPTS = 10   # 10 × 3s = 30s max wait
POLL_INTERVAL_S   = 3

class OurPackages():
    def __init__(self, db): 
        self.db = db
    
    def fetch_packages(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, amount, description, color, validity, pay, offer
                FROM packages
                ORDER BY validity
                """
            )
            return [Package(*row) for row in cursor.fetchall()]
        
    def pay(self, phone, amount, license_id, package_id):
        try:
            charge_details = Charge().stk_push(phone, amount)
        except Exception as e:
            print(f"STK push error: {e}")
            return False

        if not charge_details.get('status'):
            return False

        reference = charge_details.get('data', {}).get('reference')
        if not reference:
            return False

        # Poll with a bounded retry loop — never hang forever
        for attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL_S)
            try:
                transaction = Transactions().verify(reference=reference)
            except Exception as e:
                print(f"Verify error on attempt {attempt + 1}: {e}")
                continue

            if not transaction or not transaction.get('status'):
                continue

            status = transaction.get('data', {}).get('status')

            if status == 'success':
                self.db.update_license(license_id, package_id)
                return True
            elif status == 'failed':
                return False
            # status == 'pending' → continue polling

        print(f"Payment timed out after {MAX_POLL_ATTEMPTS} attempts: {reference}")
        return False
          
    def __call__(self):    
        if request.method == 'POST' and request.form.get('action') == 'pay':
            is_paid = self.pay(
                request.form['phone'],
                int(request.form['amount']),
                request.form['license_id'],
                request.form['package_id']
            )
            return jsonify({"success": is_paid}), 200
                
        package  = self.db.get_package_by_id(current_user.license.package_id)
        packages = self.fetch_packages()
            
        return render_template(
            'packages.html',
            page_title='Our Packages',
            helper=Helper(),
            package=package,
            packages=packages
        )