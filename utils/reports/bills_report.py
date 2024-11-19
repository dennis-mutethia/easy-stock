from datetime import datetime, timedelta
from flask import render_template, request, send_file
from io import BytesIO
from flask_login import current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils.helper import Helper
from utils.pos.bills import Bills

class BillsReport():
    def __init__(self, db): 
        self.db = db

    def generate_pdf_file(self, bills, from_date, to_date):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # Set up initial coordinates and fonts
        width, height = letter
        x_margin = 20
        y_margin = 750
        line_height = 20
        col_widths = [150, 100, 100, 50, 50, 50, 50, 0]  # Column widths matching the number of headers

        p.setFont("Helvetica-Bold", 10)
        p.drawString(150, y_margin+10, f"Customers Bills Report From {from_date} to {to_date}")
        p.setFont("Helvetica", 8)

        # Table headers
        y_position = y_margin - line_height
        headers = ["DATE TIME", "CUSTOMER", "SOLD BY", "TOTAL", "CASH", "MPESA", "BAL", ""]
        current_x = x_margin

        # Draw headers and top border
        for i, header in enumerate(headers):
            p.drawString(current_x + 5, y_position, header)  # Slightly offset text from the border
            current_x += col_widths[i]

        # Draw borders for header row
        p.line(x_margin, y_position + line_height, width - x_margin, y_position + line_height)  # Top border
        p.line(x_margin, y_position, width - x_margin, y_position)  # Bottom border

        current_x = x_margin
        for col_width in col_widths:
            p.line(current_x, y_position + line_height, current_x, y_position)  # Vertical borders
            current_x += col_width

        y_position -= line_height

        # Iterate over the bills and add each bill's details
        for bill in bills:
            if y_position < 50:  # Create a new page if necessary
                p.showPage()
                p.setFont("Helvetica", 8)
                y_position = y_margin
            
            current_x = x_margin
            bill_details = [
                str(bill.created_at),
                bill.customer.name if bill.customer else '',
                bill.user.name,
                str(int(bill.total)),
                str(int(bill.cash)),
                str(int(bill.mpesa)),
                str(int(bill.total - bill.paid)),
                ''
            ]

            # Draw the bill details and borders
            for i, detail in enumerate(bill_details):
                p.drawString(current_x + 5, y_position, detail)
                current_x += col_widths[i]
            
            # Draw borders for each row
            p.line(x_margin, y_position + line_height, width - x_margin, y_position + line_height)  # Top border
            p.line(x_margin, y_position, width - x_margin, y_position)  # Bottom border

            current_x = x_margin
            for col_width in col_widths:
                p.line(current_x, y_position + line_height, current_x, y_position)  # Vertical borders
                current_x += col_width

            y_position -= line_height

        # Finish the PDF document
        p.showPage()
        p.save()

        buffer.seek(0)
        return buffer
           
    def __call__(self):
        current_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d') #datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
        to_date = current_date
        bill_status = 0
        customer_id = 0
        page = 1
        download = 0
        
        if request.method == 'GET':   
            try:    
                from_date = request.args.get('from_date', from_date)
                to_date = request.args.get('to_date', to_date)
                bill_status = int(request.args.get('bill_status', bill_status))
                customer_id = int(request.args.get('customer_id', customer_id))
                page = int(request.args.get('page', 1))
                download = int(request.args.get('download', download))
            except ValueError as e:
                print(f"Error converting bill_status: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")               
        
        bills = Bills(self.db).fetch(from_date, to_date, bill_status, customer_id, page) 
        prev_page = page-1 if page>1 else 0
        next_page = page+1 if len(bills)==50 else 0
        grand_total = grand_paid = cash_total = mpesa_total =  0
        for bill in bills:
            grand_total = grand_total + bill.total
            grand_paid = grand_paid + bill.paid
            cash_total = cash_total + bill.cash
            mpesa_total = mpesa_total + bill.mpesa
        
        if download == 1:   
            pdf_file = self.generate_pdf_file(bills, from_date, to_date)
            return send_file(pdf_file, as_attachment=True, download_name=f"Customers_Bills_Report_from_{from_date}_to_{to_date}_{page} - {current_user.shop.name}.pdf")
        
        return render_template('reports/bills-report.html', page_title='Reports > Bills', helper=Helper(),
                               bills=bills, current_date=current_date, bill_status=bill_status, 
                                from_date=from_date, to_date=to_date, customer_id=customer_id,
                                grand_total=grand_total, grand_paid=grand_paid, cash_total=cash_total, mpesa_total=mpesa_total,
                                page=page, prev_page=prev_page, next_page=next_page)