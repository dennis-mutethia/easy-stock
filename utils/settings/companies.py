from flask import redirect, render_template, request, url_for
from flask_login import current_user

from utils.entities import Package
from utils.helper import Helper
from utils.our_packages import OurPackages

class Company():
    def __init__(self, id, name, phone, created_at, license_id, license_key, expires_at, package, validity):
        self.id = id
        self.name = name
        self.phone = phone
        self.created_at = created_at
        self.license_id = license_id
        self.license_key = license_key
        self.expires_at = expires_at
        self.package = package
        self.validity = validity
        
class Companies():
    def __init__(self, db): 
        self.db = db
            
    def fetch(self):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT c.id, c.name, u.phone, DATE(c.created_at), l.id, l.key, DATE(l.expires_at), p.name, EXTRACT(DAY FROM (l.expires_at - NOW()))
            FROM companies c
            LEFT JOIN users u ON u.id = c.created_by
            JOIN licenses l ON l.id = c.license_id
            JOIN packages p ON p.id = l.package_id
            ORDER BY c.id
            """
            #params = [current_user.company.id]
            
            cursor.execute(query)
            data = cursor.fetchall()
            companies = []
            for datum in data:   
                companies.append(Company(datum[0], datum[1], datum[2], datum[3], datum[4], datum[5], datum[6], datum[7], datum[8]))

            return companies 
       
    def update(self, id, name):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE companies 
            SET name = %s, updated_at=NOW(), updated_by = %s 
            WHERE id = %s       
            """
            cursor.execute(query, (name.upper(), current_user.id, id))
            self.db.conn.commit()
       
    def update_license(self, id, package_id):
        package = self.db.get_package_by_id(package_id)
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE licenses 
            SET package_id = %s, expires_at=NOW() + INTERVAL %s, updated_at=NOW(), updated_by = %s 
            WHERE id = %s         
            """
            cursor.execute(query, (package_id, f'+{package.validity} DAYS', current_user.id, id))
            self.db.conn.commit()
            
    def access_shop(self, shop_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE users
            SET shop_id = %s
            WHERE id = %s
            """
            cursor.execute(query, (shop_id,current_user.id))
            self.db.conn.commit()
        
    def __call__(self):   
        toastr_message = None             
        if request.method == 'POST':       
            if request.form['action'] == 'edit':  
                id = request.form['id']
                name = request.form['name'] 
                
                self.update(id, name)
                toastr_message = f'{name} Updated Successfully'
                                
            elif request.form['action'] == 'renew':
                id = request.form['id']
                package_id = request.form['package_id']
                self.update_license(id, package_id)
                toastr_message = 'License Renewed Successfully'
                                
            elif request.form['action'] == 'access':
                shop_id = request.form['id']
                self.access_shop(shop_id)
                toastr_message = 'Successfully Switched Shop'
                return redirect(url_for('companies'))
        
        companies = self.fetch() 
        packages = OurPackages(self.db).fetch_packages()
            
        return render_template('settings/companies.html', page_title='Companies', helper=Helper(),
                               companies=companies, packages=packages, toastr_message=toastr_message )