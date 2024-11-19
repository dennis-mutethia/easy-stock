from flask import render_template, request

from utils.helper import Helper

class Shop():
    def __init__(self, id, name, type, location, phone):
        self.id = id
        self.name = name
        self.type = type
        self.location = location
        self.phone = phone

class CompanyShops():
    def __init__(self, db): 
        self.db = db
    
    def fetch_shops(self, company_id):
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            SELECT s.id,s.name,st.name,s.location,s.phone_1
            FROM shops s
            LEFT JOIN shop_types st ON st.id=s.shop_type_id
            WHERE s.company_id = %s
            ORDER BY s.name ASC
            """
                        
            cursor.execute(query, (company_id,))
            data = cursor.fetchall()
            shops = []
            for datum in data:   
                shops.append(Shop(datum[0], datum[1], datum[2], datum[3], datum[4]))

            return shops 
    
    def __call__(self):
        company_id = int(request.args.get('id', 0))
        shops = self.fetch_shops(company_id)
            
        return render_template('settings/company-shops.html', helper=Helper(), 
                               shops=shops
                               )