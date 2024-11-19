from flask import render_template, request
from flask_login import current_user

from utils.entities import Package, Payment
from utils.helper import Helper
from utils.settings.system_users import SystemUsers

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
          
    def __call__(self):
        toastr_message = None   
        package_id = current_user.license.package_id
        package = self.db.get_package_by_id(package_id)  
        packages = self.fetch_packages()
            
        return render_template('packages.html', page_title='Our Packages', helper=Helper(),
                               package = package, packages = packages, toastr_message = toastr_message)