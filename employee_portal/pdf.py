from fpdf import FPDF
import os
from datetime import datetime
from pypdf import PdfReader, PdfWriter
import io

class OfferLetterPDF(FPDF):
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Elegant Orange: #e67e22 -> (230, 126, 34)
        self.set_fill_color(230, 126, 34)
        # Draw a horizontal bar as the footer
        self.rect(10, self.get_y(), 190, 1.5, 'F')

def generate_payslip_pdf(payroll):
    # Orientation set to Landscape
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # Header - Company Name
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(277, 10, txt="Gentize Innovations Private Limited", ln=True, align='C')
    
    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.PNG')
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=20, w=35)
        pdf.ln(15) 
    else:
        pdf.ln(5)

    # Title - Month and Year
    month_name = payroll.pay_period_end.strftime('%B %Y')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(277, 8, txt=f"Pay slip for the month of {month_name}", ln=True, align='L')
    pdf.ln(2)
    
    # Employee Details Section
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(277, 7, txt=" EMPLOYEE DETAILS", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 9)
    
    col_w = 277 / 3
    label_w = 35
    val_w = col_w - label_w

    # Row 1
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" Name:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.first_name} {payroll.employee.last_name}", border='B')
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" Employee ID:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.user.employeeid}", border='B')
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" Designation:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.designation.title if payroll.employee.designation else '-'}", border='RB', ln=True)
    
    # Row 2
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" Date of Joining:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.date_of_joining.strftime('%d %b %Y') if payroll.employee.date_of_joining else '-'}", border='B')
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" PAN Number:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.pan_number or '-'}", border='B')
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" Bank A/C No:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.bank_account_number or '-'}", border='RB', ln=True)

    # Row 3
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" UAN Number:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.uan_number or '-'}", border='B')
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" PF Number:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.pf_number or '-'}", border='B')
    pdf.set_font("Arial", 'B', 9); pdf.cell(label_w, 7, txt=" ESI Number:", border='LB')
    pdf.set_font("Arial", '', 9); pdf.cell(val_w, 7, txt=f"{payroll.employee.esi_number or '-'}", border='RB', ln=True)
    
    pdf.ln(3)
    
    # Salary Table Header - Added Amount Heading
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 7, txt=" EARNINGS", border=1, fill=True)
    pdf.cell(48, 7, txt=" Amount", border=1, fill=True, align='C')
    pdf.cell(90, 7, txt=" DEDUCTIONS", border=1, fill=True)
    pdf.cell(49, 7, txt=" Amount", border=1, ln=True, fill=True, align='C')
    
    # Table Content
    pdf.set_font("Arial", '', 9)
    earnings = [
        ("Basic Salary", payroll.basic),
        ("HRA", payroll.hra),
        ("Conveyance", payroll.conveyance),
        ("Medical Allowance", payroll.medical),
        ("Special Allowance", payroll.special_allowance),
        ("Bonus / Incentives", (payroll.bonus or 0) + (payroll.incentives or 0)),
        ("Reimbursements", payroll.reimbursements),
    ]
    deductions = [
        ("PF Deduction", payroll.pf),
        ("ESI Deduction", payroll.esi),
        ("Professional Tax", payroll.professional_tax),
        ("TDS / Income Tax", payroll.tds),
        ("Loss of Pay (LOP)", payroll.lop),
    ]
    
    max_rows = max(len(earnings), len(deductions))
    for i in range(max_rows):
        if i < len(earnings):
            pdf.cell(90, 6, txt=earnings[i][0], border='L')
            pdf.cell(48, 6, txt=f"{earnings[i][1]:,.2f}", border='R', align='R')
        else:
            pdf.cell(138, 6, txt="", border='LR')
        if i < len(deductions):
            pdf.cell(90, 6, txt=deductions[i][0], border=0)
            pdf.cell(49, 6, txt=f"{deductions[i][1]:,.2f}", border='R', align='R', ln=True)
        else:
            pdf.cell(139, 6, txt="", border='R', ln=True)
            
    # Totals Row
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(90, 7, txt="TOTAL EARNINGS (Gross)", border='LTB')
    pdf.cell(48, 7, txt=f"{payroll.gross_salary:,.2f}", border='RTB', align='R')
    pdf.cell(90, 7, txt="TOTAL DEDUCTIONS", border='TB')
    pdf.cell(49, 7, txt=f"{payroll.total_deductions:,.2f}", border='RTB', align='R', ln=True)
    pdf.ln(3)
    
    # Final Net Take Home
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(277, 10, txt=f"NET TAKE HOME:  INR {payroll.net_salary:,.2f}", border=1, ln=True, align='C')
    
    # Attendance Days Section
    pdf.ln(3)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(277, 7, txt=" ATTENDANCE SUMMARY", border=1, ln=True)
    pdf.set_font("Arial", '', 9)
    
    a = payroll.days_in_month or 30
    b = payroll.arrear_days or 0
    c = payroll.lopr_days or 0
    d = payroll.lop_days or 0
    e = a + b + c - d
    
    col_w_att = 277 / 5
    pdf.cell(col_w_att, 7, txt="Days In Month (A)", border=1, align='C')
    pdf.cell(col_w_att, 7, txt="Arrear Days (B)", border=1, align='C')
    pdf.cell(col_w_att, 7, txt="LOPR Days (C)", border=1, align='C')
    pdf.cell(col_w_att, 7, txt="LOP Days (D)", border=1, align='C')
    pdf.cell(col_w_att, 7, txt="Net Days Worked (E)", border=1, align='C', ln=True)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(col_w_att, 7, txt=str(a), border=1, align='C')
    pdf.cell(col_w_att, 7, txt=str(b), border=1, align='C')
    pdf.cell(col_w_att, 7, txt=str(c), border=1, align='C')
    pdf.cell(col_w_att, 7, txt=str(d), border=1, align='C')
    pdf.cell(col_w_att, 7, txt=str(e), border=1, align='C', ln=True)
    
    # Footer
    pdf.set_font("Arial", 'I', 7)
    pdf.ln(5)
    pdf.cell(277, 5, txt="This is a computer-generated document and does not require a signature.", ln=True, align='C')

    pdf_file = f"payslip_{payroll.id}.pdf"
    instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    output_path = os.path.join(instance_path, pdf_file)
    pdf.output(output_path)
    return pdf_file

def generate_offer_letter_pdf(employee, salary_structure):
    pdf = OfferLetterPDF(orientation='P', unit='mm', format='A4')
    
    # Attempt to use Poppins from local static folder or fallback
    try:
        # Check if font files exist in a local folder
        font_dir = os.path.join(os.path.dirname(__file__), 'static', 'fonts')
        pdf.add_font('Poppins', '', os.path.join(font_dir, 'Poppins-Regular.ttf'), uni=True)
        pdf.add_font('Poppins', 'B', os.path.join(font_dir, 'Poppins-Bold.ttf'), uni=True)
        pdf.add_font('Poppins', 'I', os.path.join(font_dir, 'Poppins-Italic.ttf'), uni=True)
        font_family = 'Poppins'
    except:
        font_family = 'Arial'

    # Set Margins to 1 inch (25.4 mm)
    pdf.set_margins(25.4, 25.4, 25.4)
    pdf.set_auto_page_break(auto=True, margin=25.4)
    
    # --- PAGE 1: Offer Summary ---
    pdf.add_page()
    
    # New Header with Letter_Logo.png
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'Letter_Logo.png')
    if os.path.exists(logo_path):
        # Position logo slightly higher and spans margins
        pdf.image(logo_path, x=25.4, y=10, w=159.2)
    
    # Space after header logo
    pdf.ln(25) # Reduced from 35
    
    from datetime import date
    pdf.set_font(font_family, 'B', 11)
    pdf.cell(0, 10, txt=f"Date: {date.today().strftime('%d %B %Y')}", ln=True, align='R')
    pdf.ln(5) # Reduced from 10
    
    pdf.set_font(font_family, 'B', 11)
    pdf.cell(0, 6, txt=f"To,", ln=True)
    pdf.set_font(font_family, '', 11)
    pdf.cell(0, 6, txt=f"{employee.prefix + ' ' if employee.prefix else ''}{employee.first_name} {employee.last_name}", ln=True)
    if employee.address:
        pdf.set_font(font_family, '', 11)
        pdf.multi_cell(0, 6, txt=employee.address)
    pdf.ln(5) # Reduced from 10
    
    # Heading - 13pt Bold
    pdf.set_font(font_family, 'B', 13)
    pdf.cell(0, 10, txt="Subject: Offer of Employment", ln=True, align='C', border='B')
    pdf.ln(8) # Reduced from 10
    
    # Body - 11pt, Justified alignment
    pdf.set_font(font_family, '', 11)
    intro_text = (
        f"Dear {employee.first_name},\n\n"
        f"We are pleased to extend an offer of employment to you for the position of {employee.designation.title if employee.designation else 'Employee'} "
        f"at Gentize Innovations Private Limited ('Company'). We were impressed with your qualifications and experience, "
        "and we believe that your skills will be a valuable addition to our team.\n\n"
        f"Your tentative date of joining will be {employee.date_of_joining.strftime('%d %B %Y') if employee.date_of_joining else 'Date to be decided'}.\n\n"
        "This offer is subject to the verification of your credentials and successful completion of any background checks required by the Company.\n\n"
        "The terms and conditions of your employment are set out below and in the attached annexures. "
        "Please read them carefully."
    )
    pdf.multi_cell(0, 6, txt=intro_text, align='J')
    pdf.ln(5) # Reduced from 10
    
    # Compensation Summary on Page 1
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="1. Compensation", ln=True)
    pdf.set_font(font_family, '', 11)
    ctc = salary_structure.monthly_ctc * 12 if salary_structure else 0
    comp_text = (
        f"Your Total Cost to Company (CTC) will be INR {ctc:,.2f} per annum. "
        "A detailed breakdown of your salary structure is provided in Annexure A."
    )
    pdf.multi_cell(0, 6, txt=comp_text, align='J')
    pdf.ln(15) # Reduced from 25
    
    pdf.set_font(font_family, 'B', 11)
    pdf.cell(0, 6, txt="For Gentize Innovations Private Limited,", ln=True)
    pdf.ln(15) # Adjusted for signature space
    pdf.set_font(font_family, 'B', 11)
    pdf.cell(0, 6, txt="Authorized Signatory", ln=True)
    
    # --- PAGE 2: Terms of Employment ---
    pdf.add_page()
    pdf.set_font(font_family, 'B', 14)
    pdf.cell(0, 10, txt="Terms and Conditions of Employment", ln=True, align='C', border='B')
    pdf.ln(10)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="2. Probation Period", ln=True)
    pdf.set_font(font_family, '', 11)
    pdf.multi_cell(0, 6, txt="You will be on probation for a period of 6 months from your date of joining. Upon successful completion of the probation period, your employment will be confirmed in writing. During this period, the Company reserves the right to terminate your employment with 15 days' notice or salary in lieu thereof.", align='J')
    pdf.ln(8)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="3. Working Hours", ln=True)
    pdf.set_font(font_family, '', 11)
    pdf.multi_cell(0, 6, txt="The Company's normal working hours are from 9:30 AM to 6:30 PM, Monday through Friday. However, you may be required to work additional hours depending on project requirements.", align='J')
    pdf.ln(8)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="4. Notice Period", ln=True)
    pdf.set_font(font_family, '', 11)
    pdf.multi_cell(0, 6, txt="After confirmation, either party may terminate this agreement by giving 2 months' written notice or salary in lieu of notice. The Company reserves the right to decline the buyout of notice period in case of critical project dependencies.", align='J')
    pdf.ln(8)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="5. Leaves and Holidays", ln=True)
    pdf.set_font(font_family, '', 11)
    pdf.multi_cell(0, 6, txt="You will be eligible for leaves (Casual, Sick, and Earned Leaves) as per the Company's Leave Policy. You are also entitled to public holidays as declared by the Company at the beginning of each year.", align='J')
    pdf.ln(8)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="6. Place of Work", ln=True)
    pdf.set_font(font_family, '', 11)
    pdf.multi_cell(0, 6, txt="Your initial place of posting will be at our Chennai office. However, you may be transferred to any other location, department, or branch of the Company as business needs dictate.", align='J')
    
    # --- PAGE 3: Roles & Responsibilities & Code of Conduct ---
    pdf.add_page()
    pdf.set_font(font_family, 'B', 14)
    pdf.cell(0, 10, txt="Roles, Responsibilities & Code of Conduct", ln=True, align='C', border='B')
    pdf.ln(10)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="7. Roles and Responsibilities", ln=True)
    pdf.set_font(font_family, '', 11)
    role_text = (
        "As a member of our team, you are expected to:\n"
        "- Perform duties effectively and efficiently as assigned by your reporting manager.\n"
        "- Collaborate with team members to achieve project goals and deadlines.\n"
        "- Maintain high standards of quality in your work and deliverables.\n"
        "- Continuously upgrade your skills and knowledge relevant to your role.\n"
        "- Adhere to all company processes, methodologies, and compliance standards."
    )
    pdf.multi_cell(0, 6, txt=role_text, align='J')
    pdf.ln(8)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="8. Code of Conduct - Do's and Don'ts", ln=True)
    pdf.set_font(font_family, '', 11)
    
    pdf.set_font(font_family, 'IB', 11)
    pdf.cell(0, 6, txt="Do's:", ln=True)
    pdf.set_font(font_family, '', 11)
    dos = (
        "- Do maintain professional conduct and dress code at all times.\n"
        "- Do respect colleagues, clients, and partners, fostering a diverse and inclusive environment.\n"
        "- Do communicate proactively and transparently.\n"
        "- Do protect company assets and information."
    )
    pdf.multi_cell(0, 6, txt=dos, align='J')
    pdf.ln(4)
    
    pdf.set_font(font_family, 'IB', 11)
    pdf.cell(0, 6, txt="Don'ts:", ln=True)
    pdf.set_font(font_family, '', 11)
    donts = (
        "- Don't engage in any form of harassment, discrimination, or workplace bullying.\n"
        "- Don't share confidential company information with unauthorized personnel.\n"
        "- Don't use company resources for personal gain or illegal activities.\n"
        "- Don't engage in dual employment or conflict of interest activities."
    )
    pdf.multi_cell(0, 6, txt=donts, align='J')
    
    # --- PAGE 4: Confidentiality & Acceptance ---
    pdf.add_page()
    pdf.set_font(font_family, 'B', 14)
    pdf.cell(0, 10, txt="Confidentiality & Acceptance", ln=True, align='C', border='B')
    pdf.ln(10)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="9. Confidentiality and IP Rights", ln=True)
    pdf.set_font(font_family, '', 11)
    conf_text = (
        "During your employment, you may have access to confidential information regarding the Company's business, "
        "clients, and technology. You agree to keep all such information strictly confidential and not to disclose it "
        "to any third party without prior written consent.\n\n"
        "Any intellectual property (code, designs, documentation, ideas) created by you during the course of your "
        "employment with the Company shall be the sole and exclusive property of Gentize Innovations Private Limited."
    )
    pdf.multi_cell(0, 6, txt=conf_text, align='J')
    pdf.ln(15)
    
    pdf.set_font(font_family, 'B', 12)
    pdf.cell(0, 8, txt="10. Acceptance", ln=True)
    pdf.set_font(font_family, '', 11)
    accept_text = (
        "I, __________________________________, have read and understood the terms and conditions of this "
        "offer of employment. I accept the offer and agree to abide by the Company's policies and regulations.\n\n"
        "I confirm that I will join on ____________________."
    )
    pdf.multi_cell(0, 8, txt=accept_text, align='J')
    pdf.ln(35)
    
    # Signature Block
    pdf.set_font(font_family, 'B', 11)
    pdf.cell(80, 6, txt="__________________________", ln=0)
    pdf.cell(0, 6, txt="__________________________", ln=1, align='R')
    pdf.cell(80, 6, txt="Signature", ln=0)
    pdf.cell(0, 6, txt="Date", ln=1, align='R')
    
    # Annexure A - Salary Structure
    if salary_structure:
        pdf.add_page()
        pdf.set_font(font_family, 'B', 14)
        pdf.cell(0, 10, txt="Annexure A - Salary Structure", ln=True, align='C', border='B')
        pdf.ln(10)
        
        pdf.set_font(font_family, '', 11)
        pdf.cell(40, 8, txt="Name:", ln=0)
        pdf.set_font(font_family, 'B', 11)
        pdf.cell(0, 8, txt=f"{employee.first_name} {employee.last_name}", ln=1)
        
        pdf.set_font(font_family, '', 11)
        pdf.cell(40, 8, txt="Designation:", ln=0)
        pdf.set_font(font_family, 'B', 11)
        pdf.cell(0, 8, txt=f"{employee.designation.title if employee.designation else '-'}", ln=1)
        pdf.ln(10)
        
        # Table Header
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font(font_family, 'B', 11)
        pdf.cell(90, 10, "Component", border=1, fill=True, align='C')
        pdf.cell(35, 10, "Monthly (INR)", border=1, fill=True, align='C')
        pdf.cell(35, 10, "Annual (INR)", border=1, ln=True, fill=True, align='C')
        
        components = [
            ("Basic Salary", salary_structure.basic),
            ("HRA", salary_structure.hra),
            ("Conveyance", salary_structure.conveyance),
            ("Medical Allowance", salary_structure.medical),
            ("Special Allowance", salary_structure.special_allowance),
            ("PF (Employer Contribution)", salary_structure.pf),
        ]
        
        pdf.set_font(font_family, '', 11)
        total_monthly = 0
        
        for name, value in components:
            val = value or 0.0
            total_monthly += val
            pdf.cell(90, 10, name, border=1, align='L')
            pdf.cell(35, 10, f"{val:,.2f}", border=1, align='R')
            pdf.cell(35, 10, f"{val * 12:,.2f}", border=1, ln=True, align='R')
            
        # Total Row
        pdf.set_font(font_family, 'B', 11)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(90, 10, "Total Cost to Company (CTC)", border=1, fill=True, align='L')
        pdf.cell(35, 10, f"{total_monthly:,.2f}", border=1, fill=True, align='R')
        pdf.cell(35, 10, f"{total_monthly * 12:,.2f}", border=1, fill=True, align='R', ln=True)
        
        pdf.ln(15)
        pdf.set_font(font_family, 'I', 10)
        pdf.multi_cell(0, 6, "Note: Income Tax and other statutory deductions will be applicable as per government rules.", align='C')

    pdf_file = f"Offer_Letter_{employee.user.employeeid}.pdf"
    instance_path = os.path.join(os.path.dirname(__file__), 'static', 'documents') # Save to static/documents
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    output_path = os.path.join(instance_path, pdf_file)
    pdf.output(output_path)
    return pdf_file

def generate_transactions_pdf(transactions, title, total_amount):
    # Orientation set to Landscape
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header - Company Name
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.PNG')
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=30)
        
    pdf.set_font("Arial", 'B', 16)
    # Move to the right of the logo or center? The logo is at x=10.
    # Let's Center the company name but account for logo? Or just Center as before.
    # If logo is there, maybe move Y down or put logo on side.
    # Existing code: pdf.cell(0, 10, txt="Gentize Innovations Private Limited", ln=True, align='C')
    # I'll keep it centered but maybe ensure it doesn't overlap if logo is big. 30mm width is small.
    pdf.cell(0, 10, txt="Gentize Innovations Private Limited", ln=True, align='C')
    
    # Report Title
    # pdf.set_font("Arial", 'B', 14)
    # pdf.cell(0, 10, txt=title, ln=True, align='C')
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    
    # Columns: Date (25), Category (30), Paid By (35), Description (67), Reference (35), Mode (30), Amount (35)
    
    col_date = 25
    col_cat = 30
    col_paid = 35
    col_desc = 67
    col_ref = 35
    col_mode = 30
    col_amt = 35
    
    pdf.cell(col_date, 10, "Date", border=1, fill=True, align='C')
    pdf.cell(col_cat, 10, "Category", border=1, fill=True, align='C')
    pdf.cell(col_paid, 10, "Paid By", border=1, fill=True, align='C')
    pdf.cell(col_desc, 10, "Description", border=1, fill=True, align='C')
    pdf.cell(col_ref, 10, "Reference", border=1, fill=True, align='C')
    pdf.cell(col_mode, 10, "Mode", border=1, fill=True, align='C')
    pdf.cell(col_amt, 10, "Amount (INR)", border=1, ln=True, fill=True, align='C')
    
    # Table Content
    pdf.set_font("Arial", '', 9)
    
    for t in transactions:
        date_str = t.date.strftime('%d-%b-%Y')
        desc = t.description if len(t.description) < 30 else t.description[:27] + "..."
        ref = t.reference_number or '-'
        # For Credit transactions, 'paid_by' might not exist or be relevant, handle safely
        paid_by = getattr(t, 'paid_by', '-') or '-'
        
        pdf.cell(col_date, 8, date_str, border=1, align='C')
        pdf.cell(col_cat, 8, t.category, border=1, align='C')
        pdf.cell(col_paid, 8, paid_by, border=1, align='C')
        pdf.cell(col_desc, 8, desc, border=1, align='L')
        pdf.cell(col_ref, 8, ref, border=1, align='C')
        pdf.cell(col_mode, 8, t.payment_mode, border=1, align='C')
        pdf.cell(col_amt, 8, f"{t.amount:,.2f}", border=1, ln=True, align='R')
        
    # Total Row
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(col_date + col_cat + col_paid + col_desc + col_ref + col_mode, 10, "TOTAL", border=1, fill=True, align='R')
    pdf.cell(col_amt, 10, f"{total_amount:,.2f}", border=1, fill=True, ln=True, align='R')
    
    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    from datetime import datetime
    pdf.cell(0, 5, txt=f"Generated on {datetime.now().strftime('%d %b %Y %H:%M')}", ln=True, align='R')

    filename = f"transaction_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    output_path = os.path.join(instance_path, filename)
    pdf.output(output_path)
    return filename

def generate_bill_estimate_pdf(data):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header - Logo
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.PNG')
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=30)
    
    # Header - Company Details (Right Aligned)
    pdf.set_text_color(230, 126, 34) # Elegant Orange
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 8, txt="Gentize Innovation Pvt Ltd", ln=True, align='R')
    
    pdf.set_text_color(0, 0, 0) # Reset to Black
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, txt="No.9, 2nd Floor, Saravana Complex", ln=True, align='R')
    pdf.cell(0, 5, txt="Service Road, Paraniputhur", ln=True, align='R')
    pdf.cell(0, 5, txt="Chennai - 600128, Tamil Nadu, India", ln=True, align='R')
    pdf.cell(0, 5, txt="PH: +91 7200990203", ln=True, align='R')
    pdf.cell(0, 5, txt="Email: info@gentizeinnovations.com", ln=True, align='R')
    pdf.cell(0, 5, txt="GSTIN: 33AALCG9811F1ZL", ln=True, align='R')
    
    pdf.ln(10)
    
    # Title
    pdf.set_text_color(230, 126, 34) # Elegant Orange
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="BILL ESTIMATION", ln=True, align='C')
    pdf.set_text_color(0, 0, 0) # Reset to Black
    pdf.ln(5)
    
    # Date
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, txt=f"Date: {data['date']}", ln=True, align='R')
    pdf.ln(5)
    
    # Table Header
    pdf.set_fill_color(248, 249, 250) # Light Gray
    pdf.set_text_color(73, 80, 87) # Dark Gray
    pdf.set_draw_color(230, 126, 34) # Orange Border
    pdf.set_font("Arial", 'B', 10)
    
    # Columns: Item (90), Qty (20), Price (40), Total (40)
    col_item = 90
    col_qty = 20
    col_price = 40
    col_total = 40
    
    # Draw top border/fill
    # Use 'B' for bottom border? FPDF cell borders: 1 (all), 0 (no), L, T, R, B
    # We want fill and bottom border.
    pdf.cell(col_item, 10, "ITEM DESCRIPTION", border='B', fill=True, align='L')
    pdf.cell(col_qty, 10, "QTY", border='B', fill=True, align='C')
    pdf.cell(col_price, 10, "PRICE (INR)", border='B', fill=True, align='R')
    pdf.cell(col_total, 10, "TOTAL (INR)", border='B', ln=True, fill=True, align='R')
    
    # Reset colors for content
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(200, 200, 200) # Light Gray for inner lines if needed, or just 0
    pdf.set_font("Arial", '', 9)
    
    items = data.get('items', [])
    for item in items:
        # Use simple bottom border for rows
        pdf.cell(col_item, 10, item.get('description', ''), border='B', align='L')
        pdf.cell(col_qty, 10, str(item.get('qty', '')), border='B', align='C')
        pdf.cell(col_price, 10, f"{float(item.get('price', 0)):,.2f}", border='B', align='R')
        pdf.cell(col_total, 10, f"{float(item.get('total', 0)):,.2f}", border='B', ln=True, align='R')
        
    # Total Row
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    # No fill for total row in PO example, just text at end.
    # PO Example:
    # Subtotal ...
    # Tax ...
    # Total (Orange) ...
    
    # We only have Total Amount in data right now.
    pdf.set_text_color(230, 126, 34) # Orange
    pdf.cell(col_item + col_qty + col_price, 10, "TOTAL", border=0, fill=False, align='R')
    pdf.cell(col_total, 10, f"{data.get('total_amount', 0):,.2f}", border=0, fill=False, ln=True, align='R')
    pdf.set_text_color(0, 0, 0)
    
    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, txt="This is a computer-generated estimate.", ln=True, align='C')

    filename = f"Bill_Estimate_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    output_path = os.path.join(instance_path, filename)
    pdf.output(output_path)
    return filename

def generate_letter_head_pdf(data):
    # Sanitize content to avoid UnicodeEncodeError with standard PDF fonts
    content = data['content']
    replacements = {
        '\u2018': "'", '\u2019': "'",  # Smart single quotes
        '\u201c': '"', '\u201d': '"',  # Smart double quotes
        '\u2013': '-', '\u2014': '--', # En and em dashes
        '\u2026': '...'                # Ellipsis
    }
    for old, new in replacements.items():
        content = content.replace(old, new)

    # 1. Create content PDF using FPDF
    content_pdf = FPDF(orientation='P', unit='mm', format='A4')
    content_pdf.add_page()
    content_pdf.set_auto_page_break(auto=True, margin=20)
    
    # Set Margins (adjust based on template)
    content_pdf.set_y(40) 
    content_pdf.set_x(25)
    
    # Date
    content_pdf.set_font("Arial", '', 11)
    content_pdf.cell(0, 10, txt=f"Date: {data['date']}", ln=True, align='R')
    content_pdf.ln(10)
    
    # Content
    content_pdf.set_font("Arial", '', 11)
    content_pdf.multi_cell(0, 6, txt=content, align='J')
    content_pdf.ln(20)

    # Save to memory
    # FPDF.output(dest='S') returns the PDF as a string/bytes
    content_raw = content_pdf.output(dest='S')
    
    # Handle both string (standard fpdf) and bytes (fpdf2)
    if isinstance(content_raw, str):
        content_bytes = content_raw.encode('latin-1')
    else:
        content_bytes = content_raw
        
    content_stream = io.BytesIO(content_bytes)
    
    # 2. Merge with template
    template_path = os.path.join(os.path.dirname(__file__), 'static', 'templates', 'Letter_Head_template.pdf')
    
    if not os.path.exists(template_path):
        # Fallback if template missing
        filename = f"Letter_Head_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
        if not os.path.exists(instance_path): os.makedirs(instance_path)
        output_path = os.path.join(instance_path, filename)
        content_pdf.output(output_path)
        return filename

    reader = PdfReader(template_path)
    writer = PdfWriter()
    
    content_reader = PdfReader(content_stream)
    
    # Merge first page
    page = reader.pages[0]
    page.merge_page(content_reader.pages[0])
    writer.add_page(page)
    
    # Add remaining pages from content if any
    for i in range(1, len(content_reader.pages)):
        try:
            template_reader = PdfReader(template_path)
            new_page = template_reader.pages[0]
            new_page.merge_page(content_reader.pages[i])
            writer.add_page(new_page)
        except:
            writer.add_page(content_reader.pages[i])

    filename = f"Letter_Head_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    output_path = os.path.join(instance_path, filename)
    
    with open(output_path, "wb") as f:
        writer.write(f)
        
    return filename