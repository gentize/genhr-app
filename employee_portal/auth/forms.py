from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, FileField, FloatField, DateField, HiddenField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, Regexp
from flask_wtf.file import FileField, FileAllowed
from employee_portal.models import User, Role, AuthorizedSignature
from datetime import date
from wtforms import widgets
from employee_portal.utils.helpers import get_vendors
from wtforms_sqlalchemy.fields import QuerySelectField

# --- Helper Functions ---

def get_roles():
    try:
        return Role.query.all()
    except:
        return []

def get_designations():
    try:
        return Designation.query.all()
    except:
        return []

def get_departments():
    try:
        return Department.query.all()
    except:
        return []

def get_employees():
    try:
        return EmployeeProfile.query.filter_by(is_resigned=False).order_by(EmployeeProfile.first_name).all()
    except:
        return []

def get_all_users():
    return User.query.all()

# --- Forms ---

class LoginForm(FlaskForm):
    employeeid = StringField('Employee ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    employeeid = StringField('Employee ID', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    def validate_employeeid(self, employeeid):
        user = User.query.filter_by(employeeid=employeeid.data).first()
        if user is not None:
            raise ValidationError('Please use a different Employee ID.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField(
        'Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password', render_kw={"class": "mt-4"})

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class RoleForm(FlaskForm):
    name = QuerySelectField('Role Name (from Designations)', query_factory=get_designations, get_label='title', allow_blank=False, validators=[DataRequired()])
    permissions = MultiCheckboxField('Permissions', choices=[
        ('dashboard', 'Dashboard'),
        ('view_employees', 'View Employees (Team)'),
        ('add_employee', 'Onboard Employee'),
        ('designations', 'Manage Designations'),
        ('attendance', 'View Attendance'),
        ('view_assets', 'View Assets'),
        ('add_asset', 'Add/Edit Asset'),
        ('view_vendors', 'View Vendors'),
        ('add_vendor', 'Add/Edit Vendor'),
        ('manage_payroll', 'Manage Payroll'),
        ('roles', 'Manage Roles'),
        ('change_role', 'Change User Role'),
        ('manage_ats', 'Manage Recruitment (ATS)'),
        ('checklist', 'Manage Checklists'),
        ('view_shifts', 'View Shift Plan'),
        ('edit_shifts', 'Edit Shift Plan')
    ])
    submit = SubmitField('Save Role')

class JobOpeningForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired()])
    department = QuerySelectField('Department', query_factory=get_departments, get_label='name', allow_blank=True)
    description = StringField('Description', widget=widgets.TextArea())
    status = SelectField('Status', choices=[('Open', 'Open'), ('Closed', 'Closed'), ('On Hold', 'On Hold')], default='Open')
    submit = SubmitField('Save Job')

class CandidateForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone')
    job_opening = QuerySelectField('Applied For', query_factory=lambda: JobOpening.query.filter_by(status='Open').all(), get_label='title', allow_blank=True)
    status = SelectField('Status', choices=[('Applied', 'Applied'), ('Interviewing', 'Interviewing'), ('Offered', 'Offered'), ('Hired', 'Hired'), ('Rejected', 'Rejected')], default='Applied')
    submit = SubmitField('Save Candidate')

class TaskForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    task_type = SelectField('Type', choices=[('Onboarding', 'Onboarding'), ('Offboarding', 'Offboarding'), ('Others', 'Others')], default='Onboarding')
    other_type_name = StringField('Other Type Details')
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Low')
    assigned_role = QuerySelectField('Responsible Role', query_factory=get_roles, get_label='name', allow_blank=True)
    task_add_to = QuerySelectField('Task Add To (Optional)', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name}", allow_blank=True, blank_text='All Role Members')
    target_date = DateField('Target Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Save Task')

class AppraisalForm(FlaskForm):
    employee = QuerySelectField('Employee', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name}", allow_blank=False)
    period = StringField('Period (e.g., 2025 Q1)', validators=[DataRequired()])
    score = SelectField('Score (1-5)', choices=[(1, '1 - Poor'), (2, '2 - Needs Improvement'), (3, '3 - Meets Expectations'), (4, '4 - Exceeds Expectations'), (5, '5 - Outstanding')], coerce=int, default=3)
    feedback = StringField('Feedback', widget=widgets.TextArea(), validators=[DataRequired()])
    goals = StringField('Goals for Next Period', widget=widgets.TextArea())
    status = SelectField('Status', choices=[('Draft', 'Draft'), ('Finalized', 'Finalized')], default='Draft')
    submit = SubmitField('Save Appraisal')

class ExpenseClaimForm(FlaskForm):
    title = StringField('Title/Purpose', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Travel', 'Travel'), ('Food', 'Food'), ('Supplies', 'Supplies'), ('Other', 'Other')], default='Travel')
    date_occurred = DateField('Date of Expense', format='%Y-%m-%d', validators=[DataRequired()])
    receipt = FileField('Upload Receipt', validators=[FileAllowed(['jpg', 'png', 'pdf'])])
    submit = SubmitField('Submit Claim')

class HolidayForm(FlaskForm):
    name = StringField('Holiday Name', validators=[DataRequired()])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    description = StringField('Description')
    submit = SubmitField('Save Holiday')

class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = StringField('Content', widget=widgets.TextArea(), validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Post Announcement')

class EmployeeDocumentForm(FlaskForm):
    title = StringField('Document Title', validators=[DataRequired()])
    document_type = SelectField('Type', choices=[('ID Proof', 'ID Proof'), ('Contract', 'Contract'), ('Offer Letter', 'Offer Letter'), ('Policy', 'Policy'), ('Other', 'Other')], default='Other')
    file = FileField('Upload Document', validators=[DataRequired(), FileAllowed(['jpg', 'png', 'pdf', 'docx'])])
    submit = SubmitField('Upload')

class DesignationForm(FlaskForm):
    title = StringField('Designation Title', validators=[DataRequired()])
    role = QuerySelectField('Default Role', query_factory=get_roles, get_label='name', allow_blank=True, blank_text='Select Role')
    submit = SubmitField('Save')

class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired()])
    submit = SubmitField('Save')

class AdminAddEmployeeForm(FlaskForm):
    # Personal Information
    prefix = SelectField('Prefix', choices=[('', 'Select'), ('Mr', 'Mr'), ('Miss', 'Miss'), ('Mrs', 'Mrs')], validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    marital_status = SelectField('Marital Status', choices=[('', 'Select'), ('Married', 'Married'), ('Single', 'Single')], validators=[DataRequired()])
    
    address = StringField('Home Address', validators=[DataRequired()])
    phone_number = StringField('Mobile Number', validators=[DataRequired(), Regexp(r'^\d{10}$', message="Mobile number must be 10 digits.")])
    email = StringField('Email', validators=[DataRequired(), Email()])
    
    pan_number = StringField('PAN Number', validators=[DataRequired(), Length(min=10)])
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired(), Length(min=12)])
    uan_number = StringField('UAN Number')
    pf_number = StringField('PF Number')
    esi_number = StringField('ESI Number')
    emergency_contact = StringField('Emergency Contact', validators=[DataRequired()])
    
    bank_account_number = StringField('Bank Account Number', validators=[DataRequired()])
    bank_name = StringField('Bank Name', validators=[DataRequired()])
    ifsc_code = StringField('IFSC Code', validators=[DataRequired()])
    branch = StringField('Branch', validators=[DataRequired()])
    
    # Job Information
    department = QuerySelectField('Department', query_factory=get_departments, get_label='name', allow_blank=True, blank_text='Select Department')
    designation = QuerySelectField('Designation', query_factory=get_designations, get_label='title', allow_blank=True, blank_text='Select Designation', validators=[DataRequired()])
    reports_to = QuerySelectField('Reports To', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name}", allow_blank=True, blank_text='Select Manager')
    previous_employer = StringField('Previous Employer')
    years_of_experience = StringField('Years of Experience')
    employment_type = SelectField('Employment Type', choices=[('Full-time', 'Full-time'), ('Probation', 'Probation'), ('Training', 'Training')], default='Full-time')
    date_of_joining = DateField('Date of Joining', format='%Y-%m-%d', validators=[DataRequired()])
    
    is_resigned = BooleanField('Resigned')
    notice_period = SelectField('Notice Period', choices=[('', 'Select'), ('1', '1 Month'), ('2', '2 Month'), ('3', '3 Month')], default='', validators=[Optional()])
    resigned_date = DateField('Resigned Date', format='%Y-%m-%d', validators=[Optional()])
    
    # Credentials
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    picture = FileField('Upload Picture', validators=[FileAllowed(['jpg', 'png'])])
    
    submit = SubmitField('Onboard Employee')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class AdminEditEmployeeForm(FlaskForm):
    # Credential Fields (Merged)
    employeeid = StringField('Employee ID', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('New Password (leave blank to keep current)', validators=[Optional()])
    password2 = PasswordField('Repeat Password', validators=[EqualTo('password')])

    # Personal Information
    prefix = SelectField('Prefix', choices=[('', 'Select'), ('Mr', 'Mr'), ('Miss', 'Miss'), ('Mrs', 'Mrs')], validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    marital_status = SelectField('Marital Status', choices=[('', 'Select'), ('Married', 'Married'), ('Single', 'Single')], validators=[DataRequired()])
    
    address = StringField('Home Address', validators=[DataRequired()])
    phone_number = StringField('Mobile Number', validators=[DataRequired(), Regexp(r'^\d{10}$', message="Mobile number must be 10 digits.")])
    
    pan_number = StringField('PAN Number', validators=[DataRequired(), Length(min=10)])
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired(), Length(min=12)])
    uan_number = StringField('UAN Number')
    pf_number = StringField('PF Number')
    esi_number = StringField('ESI Number')
    emergency_contact = StringField('Emergency Contact', validators=[DataRequired()])
    
    bank_account_number = StringField('Bank Account Number', validators=[DataRequired()])
    bank_name = StringField('Bank Name', validators=[DataRequired()])
    ifsc_code = StringField('IFSC Code', validators=[DataRequired()])
    branch = StringField('Branch', validators=[DataRequired()])
    
    # Job Information
    department = QuerySelectField('Department', query_factory=get_departments, get_label='name', allow_blank=True, blank_text='Select Department')
    designation = QuerySelectField('Designation', query_factory=get_designations, get_label='title', allow_blank=True, blank_text='Select Designation', validators=[DataRequired()])
    reports_to = QuerySelectField('Reports To', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name}", allow_blank=True, blank_text='Select Manager')
    previous_employer = StringField('Previous Employer')
    years_of_experience = StringField('Years of Experience')
    employment_type = SelectField('Employment Type', choices=[('Full-time', 'Full-time'), ('Probation', 'Probation'), ('Training', 'Training')], default='Full-time')
    date_of_joining = DateField('Date of Joining', format='%Y-%m-%d', validators=[DataRequired()])
    
    is_resigned = BooleanField('Resigned')
    notice_period = SelectField('Notice Period', choices=[('', 'Select'), ('1', '1 Month'), ('2', '2 Month'), ('3', '3 Month')], default='', validators=[Optional()])
    resigned_date = DateField('Resigned Date', format='%Y-%m-%d', validators=[Optional()])

    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update Employee')

    def __init__(self, original_user_id=None, *args, **kwargs):
        super(AdminEditEmployeeForm, self).__init__(*args, **kwargs)
        self.original_user_id = original_user_id

    def validate_employeeid(self, employeeid):
        user = User.query.filter_by(employeeid=employeeid.data).first()
        if user is not None and user.id != self.original_user_id:
            raise ValidationError('That Employee ID is already taken.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None and user.id != self.original_user_id:
            raise ValidationError('That email is already taken.')

class SalaryStructureForm(FlaskForm):
    employee = QuerySelectField('Employee', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name}")
    monthly_ctc = FloatField('Monthly CTC (Fixed)', validators=[DataRequired()])
    
    basic = FloatField('Basic Salary', default=0.0)
    hra = FloatField('HRA', default=0.0)
    conveyance = FloatField('Conveyance', default=0.0)
    medical = FloatField('Medical Allowance', default=0.0)
    special_allowance = FloatField('Special Allowance', default=0.0)
    
    pf = FloatField('PF Deduction', default=0.0)
    esi = FloatField('ESI Deduction', default=0.0)
    professional_tax = FloatField('Professional Tax', default=0.0)
    
    submit = SubmitField('Update Structure')

class PayrollForm(FlaskForm):
    employee = QuerySelectField('Employee', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name}")
    pay_period_start = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    pay_period_end = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    # Pre-filled from structure, but editable
    basic = FloatField('Basic', default=0.0)
    hra = FloatField('HRA', default=0.0)
    conveyance = FloatField('Conveyance', default=0.0)
    medical = FloatField('Medical', default=0.0)
    special_allowance = FloatField('Special Allowance', default=0.0)
    
    # Variable
    bonus = FloatField('Bonus', default=0.0)
    incentives = FloatField('Incentives', default=0.0)
    reimbursements = FloatField('Expense Reimbursement', default=0.0)
    
    # Deductions
    pf = FloatField('PF', default=0.0)
    esi = FloatField('ESI', default=0.0)
    professional_tax = FloatField('Prof. Tax', default=0.0)
    tds = FloatField('TDS (Income Tax)', default=0.0)
    lop = FloatField('Loss of Pay (Deduction)', default=0.0)
    
    status = SelectField('Status', choices=[('Draft', 'Draft'), ('Processed', 'Processed'), ('Paid', 'Paid')], default='Draft')
    
    # Day Counts
    days_in_month = FloatField('Days in Month (A)', default=30.0)
    arrear_days = FloatField('Arrear Days (B)', default=0.0)
    lopr_days = FloatField('LOPR Days (C)', default=0.0)
    lop_days = FloatField('LOP Days (D)', default=0.0)
    
    submit = SubmitField('Process Payroll')

    def validate_serial_number(self, serial_number):
        pass

class AdminChangeUserRoleForm(FlaskForm):
    user_id = QuerySelectField('Employee', query_factory=get_all_users, get_label=lambda u: f"{u.employeeid} ({u.email})")
    role = QuerySelectField('New Role', query_factory=get_roles, get_label='name', validators=[DataRequired()])
    submit = SubmitField('Change Role')

class VendorForm(FlaskForm):
    name = StringField('Vendor Name', validators=[DataRequired()])
    category = SelectField('Category', choices=[('IT', 'IT Services'), ('Facility', 'Facility Management'), ('Logistics', 'Logistics'), ('Recruitment', 'Recruitment'), ('Consultancy', 'Consultancy'), ('Other', 'Other')], default='IT')
    contact_person = StringField('Contact Person')
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone')
    address = StringField('Address', widget=widgets.TextArea())
    services_provided = StringField('Services Provided')
    
    # Financials
    gstin = StringField('GSTIN / Tax ID')
    bank_account = StringField('Bank Account Number')
    bank_name = StringField('Bank Name')
    ifsc_code = StringField('IFSC Code')
    payment_terms = SelectField('Payment Terms', choices=[('Due on Receipt', 'Due on Receipt'), ('Net 15', 'Net 15'), ('Net 30', 'Net 30'), ('Advance', 'Advance')], default='Net 30')
    
    # Contract
    contract_start = DateField('Contract Start Date', format='%Y-%m-%d', validators=[Optional()])
    contract_expiry = DateField('Contract Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive'), ('Blacklisted', 'Blacklisted')], default='Active')
    
    submit = SubmitField('Save Vendor')

def get_vendors():
    try:
        return Vendor.query.all()
    except:
        return []

class AssetForm(FlaskForm):
    name = StringField('Asset Name', validators=[DataRequired()])
    brand = StringField('Brand')
    model_name = StringField('Model Name')
    category = SelectField('Category', choices=[('Laptop', 'Laptop'), ('Mobile', 'Mobile'), ('Tablet', 'Tablet'), ('Monitor', 'Monitor'), ('Furniture', 'Furniture'), ('Peripherals', 'Peripherals'), ('Other', 'Other')], default='Laptop')
    serial_number = StringField('Serial Number', validators=[DataRequired()])
    
    condition = SelectField('Condition', choices=[('New', 'New'), ('Good', 'Good'), ('Fair', 'Fair'), ('Damaged', 'Damaged'), ('Scrapped', 'Scrapped')], default='New')
    status = SelectField('Status', choices=[('Available', 'Available'), ('Assigned', 'Assigned'), ('Maintenance', 'Maintenance'), ('Scrapped', 'Scrapped')], default='Available')
    
    purchase_date = DateField('Purchase Date', format='%Y-%m-%d', validators=[Optional()])
    purchase_cost = FloatField('Purchase Cost', validators=[Optional()])
    warranty_expiry = DateField('Warranty Expiry', format='%Y-%m-%d', validators=[Optional()])
    
    vendor = QuerySelectField('Vendor / Owner', query_factory=get_vendors, get_label='name', allow_blank=True, blank_text='-- Internal (Gentize) --')
    assigned_to = QuerySelectField('Assigned To', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name} ({e.user.employeeid})", allow_blank=True, blank_text='-- Available --')
    submit = SubmitField('Save Asset')

    def validate_serial_number(self, serial_number):
        pass

class CreditForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    description = StringField('Description', widget=widgets.TextArea())
    category = SelectField('Category', choices=[('Sales', 'Sales'), ('Investment', 'Investment'), ('Refund', 'Refund'), ('Other', 'Other')], default='Sales')
    payment_mode = SelectField('Payment Mode', choices=[('Bank Transfer', 'Bank Transfer'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('UPI', 'UPI')], default='Bank Transfer')
    reference_number = StringField('Reference Number')
    submit = SubmitField('Save Credit')

class DebitForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    description = StringField('Description', widget=widgets.TextArea())
    category = SelectField('Category', choices=[('Salary', 'Salary'), ('Rent', 'Rent'), ('Utilities', 'Utilities'), ('Purchase', 'Purchase'), ('Other', 'Other')], default='Purchase')
    payment_mode = SelectField('Payment Mode', choices=[('Bank Transfer', 'Bank Transfer'), ('Cash', 'Cash'), ('Cheque', 'Cheque'), ('UPI', 'UPI')], default='Bank Transfer')
    reference_number = StringField('Reference Number')
    paid_by = SelectField('Paid By', choices=[], validate_choice=False) # Choices populated dynamically
    bill = FileField('Attach Bill', validators=[FileAllowed(['pdf', 'jpg', 'png'], 'Documents only!')])
    submit = SubmitField('Save Debit')

class InvoiceForm(FlaskForm):
    invoice_number = StringField('Invoice Number', validators=[DataRequired()])
    date = DateField('Invoice Date', format='%Y-%m-%d', validators=[DataRequired()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    vendor = QuerySelectField('Vendor', query_factory=get_vendors, get_label='name', allow_blank=False)
    amount = FloatField('Amount', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid'), ('Overdue', 'Overdue'), ('Cancelled', 'Cancelled')], default='Unpaid')
    description = StringField('Description', widget=widgets.TextArea())
    file = FileField('Upload Invoice', validators=[FileAllowed(['pdf', 'jpg', 'png'], 'Documents only!')])
    submit = SubmitField('Save Invoice')

class BillEstimationForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    items_json = HiddenField('Items JSON')
    total_amount = FloatField('Total Amount')
    submit = SubmitField('Generate Estimate')

def get_signatures():
    try:
        return AuthorizedSignature.query.all()
    except:
        return []

class AuthorizedSignatureForm(FlaskForm):
    name = StringField('Name of Signatory', validators=[DataRequired()])
    designation = StringField('Designation', validators=[DataRequired()])
    file = FileField('Upload Signature Image', validators=[DataRequired(), FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Upload Signature')

class PurchaseOrderForm(FlaskForm):
    po_number = StringField('PO Number', validators=[DataRequired()])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    vendor = QuerySelectField('Vendor', query_factory=get_vendors, get_label='name', allow_blank=False)
    
    # Items can be handled dynamically in frontend, passing JSON or just a simple text area for now
    items_json = StringField('Items JSON', widget=widgets.HiddenInput()) 
    
    tax_percentage = FloatField('Tax (%)', default=0.0, validators=[Optional()])
    total_amount = FloatField('Total Amount', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Draft', 'Draft'), ('Sent', 'Sent'), ('Approved', 'Approved'), ('Paid', 'Paid'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Draft')
    authorized_signature = QuerySelectField('Authorized Signature', query_factory=get_signatures, get_label='name', allow_blank=True)
    notes = StringField('Notes', widget=widgets.TextArea())
    submit = SubmitField('Save Purchase Order')

class ShiftForm(FlaskForm):
    employee = QuerySelectField('Employee', query_factory=get_employees, get_label=lambda e: f"{e.first_name} {e.last_name} ({e.user.employeeid})", allow_blank=False)
    date = DateField('From Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('To Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    shift_type = SelectField('Shift Type', choices=[
        ('General', 'General Shift (8 AM - 5:30 PM)'),
        ('Morning', 'Morning Shift (6 AM - 2 PM)'),
        ('Noon', 'Noon Shift (2 PM - 10 PM)'),
        ('Night', 'Night Shift (10 PM - 6 AM)')
    ], validators=[DataRequired()])
    submit = SubmitField('Assign Shift')
class LetterHeadForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    content = TextAreaField('Content', validators=[DataRequired()])
    authorized_signature = QuerySelectField('Signature', query_factory=get_signatures, get_label='name', allow_blank=False, validators=[DataRequired()])
    submit = SubmitField('Generate Letter Head')

