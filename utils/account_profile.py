from flask import render_template, request
from flask_login import current_user

from utils.helper import Helper
from utils.settings.system_users import SystemUsers

class AccountProfile():
    def __init__(self, db): 
        self.db = db
             
    def __call__(self):
        toastr_message = None
                
        if request.method == 'POST':       
            if request.form['action'] == 'update':  
                name = request.form['name']
                phone = request.form['phone']   
                password = request.form['password']                  
                SystemUsers(self.db).update(current_user.id, name, phone, current_user.user_level.id, current_user.shop.id, password)
                toastr_message = 'Profile Updated Successfully'        
        
        return render_template('account-profile.html', page_title='My Account Profile', helper=Helper(), 
                               toastr_message = toastr_message)