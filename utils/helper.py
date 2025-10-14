import hashlib

from flask_login import current_user

class Helper():
    def __init__(self, db=None):
        self.db = db
    
    def hash_password(self, password):
        password_bytes = password.encode('utf-8')
        hash_object = hashlib.sha256(password_bytes)
        return hash_object.hexdigest()
    
    def format_number(self, number):
        if isinstance(number, float):
            if number.is_integer():
                return int(number)
            return number
        return number

    # Custom filter function
    def format_number_with_commas(self, value):
        if isinstance(value, (int, float)):
            return "{:,.0f}".format(value)
        else:
            return value
           
    def update_license(self, id, package_id):
        package = self.db.get_package_by_id(package_id)
        self.db.ensure_connection()
        with self.db.conn.cursor() as cursor:
            query = """
            UPDATE licenses 
            SET 
                package_id = %s, 
                expires_at = CASE 
                                WHEN expires_at > CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' THEN expires_at + INTERVAL %s 
                                ELSE CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi' + INTERVAL %s 
                            END, 
                updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Nairobi', 
                updated_by = %s 
            WHERE id = %s   
            """
            cursor.execute(query, (package_id, f'+{package.validity} DAYS', f'+{package.validity} DAYS', current_user.id, id))
            self.db.conn.commit()