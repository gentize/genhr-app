from . import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.Column(db.Text) # Comma-separated list

    def __repr__(self):
        return f'<Role {self.name}>'
        
    def has_permission(self, perm):
        if not self.permissions: return False
        return perm in self.permissions.split(',')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employeeid = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    user_role = db.relationship('Role', backref='users')
    
    is_first_login = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def is_online(self):
        if not self.last_seen:
            return False
        # Online if active in last 5 minutes
        return (datetime.utcnow() - self.last_seen).total_seconds() < 300

    # Backward compatibility property
    @property
    def role(self):
        if self.user_role:
            return self.user_role.name.lower()
        return 'employee' # Default if no role assigned

    def has_permission(self, perm):
        if self.user_role:
            return self.user_role.has_permission(perm)
        return False

    profile = db.relationship('EmployeeProfile', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.employeeid}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class Designation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)
    role = db.relationship('Role', backref='designations')

    def __repr__(self):
        return f'<Designation {self.title}>'

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), default='General') # IT, Facility, Logistics, etc.
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    services_provided = db.Column(db.String(200)) 
    
    # Financial & Tax
    gstin = db.Column(db.String(20))
    bank_account = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    ifsc_code = db.Column(db.String(20))
    payment_terms = db.Column(db.String(50)) # e.g. Net 30, Advance
    
    # Contract
    contract_start = db.Column(db.Date)
    contract_expiry = db.Column(db.Date)
    status = db.Column(db.String(20), default='Active') # Active, Inactive, Blacklisted
    
    assets = db.relationship('Asset', backref='vendor_ref', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='vendor', lazy='dynamic')
    purchase_orders = db.relationship('PurchaseOrder', backref='vendor', lazy='dynamic')
    
    def __repr__(self):
        return f'<Vendor {self.name}>'

class AuthorizedSignature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100))
    file_path = db.Column(db.String(255), nullable=False) # Path to signature image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Signature {self.name}>'

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(100), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    
    # Item Details (JSON or Text for simplicity in this iteration, or separate table)
    # Storing as JSON string for flexibility: [{"item": "Laptop", "qty": 2, "rate": 50000, "amount": 100000}, ...]
    items_json = db.Column(db.Text) 
    
    tax_percentage = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Draft') # Draft, Sent, Approved, Completed, Cancelled
    notes = db.Column(db.Text)
    
    signature_id = db.Column(db.Integer, db.ForeignKey('authorized_signature.id'), nullable=True)
    signature = db.relationship('AuthorizedSignature')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PurchaseOrder {self.po_number}>'

class Credit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    category = db.Column(db.String(100)) # e.g., Sales, Investment, Refund
    payment_mode = db.Column(db.String(50)) # e.g., Bank Transfer, Cash, Cheque
    reference_number = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Credit {self.id} - {self.amount}>'

class Debit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    category = db.Column(db.String(100)) # e.g., Salary, Rent, Utilities
    payment_mode = db.Column(db.String(50))
    reference_number = db.Column(db.String(100))
    bill_file = db.Column(db.String(255)) # Path to uploaded bill/receipt
    paid_by = db.Column(db.String(100)) # Name of the person who paid (Director)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Debit {self.id} - {self.amount}>'

class ShiftSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    employee = db.relationship('EmployeeProfile', backref='shifts')
    
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False) # Morning, Noon, Night
    
    assigned_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure one shift per employee per day
    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='_employee_shift_uc'),)

    def __repr__(self):
        return f'<Shift {self.shift_type} - {self.employee.first_name} on {self.date}>'

class BillEstimate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estimate_number = db.Column(db.String(50), unique=True) # E.g., EST-2025-001
    date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    items_json = db.Column(db.Text) # JSON string of items
    pdf_file = db.Column(db.String(255)) # Path to generated PDF
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BillEstimate {self.estimate_number}>'

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Unpaid') # Unpaid, Paid, Overdue, Cancelled
    description = db.Column(db.String(255))
    file_path = db.Column(db.String(255)) # Path to uploaded invoice file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Department {self.name}>'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50))
    model_name = db.Column(db.String(50))
    category = db.Column(db.String(50), default='Laptop') 
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    
    condition = db.Column(db.String(20), default='New') 
    status = db.Column(db.String(20), default='Available') 
    
    purchase_date = db.Column(db.Date)
    purchase_cost = db.Column(db.Float)
    warranty_expiry = db.Column(db.Date)
    
    owned_by = db.Column(db.String(100)) # Kept for backward compatibility or direct text
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True)
    
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    history = db.relationship('AssetHistory', backref='asset', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Asset {self.name} - {self.serial_number}>'

class AssetHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=True)
    employee = db.relationship('EmployeeProfile')
    
    action = db.Column(db.String(50)) # Assigned, Returned, Maintenance
    notes = db.Column(db.String(200))
    date_action = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by = db.Column(db.String(100))

    def __repr__(self):
        return f'<AssetHistory {self.action} for asset {self.asset_id}>'

class EmployeeProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(db.String(120), unique=True, index=True)
    
    # Personal Info
    prefix = db.Column(db.String(10))
    gender = db.Column(db.String(10))
    marital_status = db.Column(db.String(20))
    phone_number = db.Column(db.String(20))
    address = db.Column(db.String(200))
    date_of_birth = db.Column(db.Date)
    
    # IDs & Bank
    pan_number = db.Column(db.String(20))
    aadhar_number = db.Column(db.String(20))
    uan_number = db.Column(db.String(20))
    pf_number = db.Column(db.String(50))
    esi_number = db.Column(db.String(50))
    emergency_contact = db.Column(db.String(20))
    bank_account_number = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    ifsc_code = db.Column(db.String(20))
    branch = db.Column(db.String(100))

    # Job Info
    date_of_joining = db.Column(db.Date, default=datetime.utcnow)
    
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    department = db.relationship('Department', backref='employees')
    
    designation_id = db.Column(db.Integer, db.ForeignKey('designation.id'))
    designation = db.relationship('Designation', backref='employees')
    
    reports_to_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=True)
    manager = db.relationship('EmployeeProfile', remote_side=[id], backref='subordinates')
    
    @property
    def reports_to(self):
        if self.manager:
            return f"{self.manager.first_name} {self.manager.last_name}"
        return None

    previous_employer = db.Column(db.String(100))
    years_of_experience = db.Column(db.String(20))
    
    is_resigned = db.Column(db.Boolean, default=False)
    resigned_date = db.Column(db.Date, nullable=True) # This acts as Date of Leaving
    notice_period = db.Column(db.String(20), nullable=True) # '1', '2', '3' months
    employment_type = db.Column(db.String(20), default='Full-time') # 'Probation', 'Training', 'Full-time'
    
    @property
    def is_effectively_resigned(self):
        from datetime import date
        if self.is_resigned and self.resigned_date:
            return self.resigned_date <= date.today()
        return self.is_resigned

    @property
    def status_info(self):
        from datetime import date
        if not self.is_resigned:
            return {'text': 'Active', 'class': 'bg-active-green'}
        
        if self.resigned_date and self.resigned_date > date.today():
            return {'text': 'Notice Period', 'class': 'bg-primary'} # Elegant Orange
        
        return {'text': 'Resigned', 'class': 'bg-danger'}
    
    @property
    def is_online(self):
        return self.user.is_online if self.user else False

    image_file = db.Column(db.String(20), nullable=True, default='default.jpg')
    biometric_image = db.Column(db.String(100), nullable=True) # Reference for face recognition
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    attendances = db.relationship('Attendance', backref='employee', lazy='dynamic', cascade="all, delete-orphan")
    payrolls = db.relationship('Payroll', backref='employee', lazy='dynamic', cascade="all, delete-orphan")
    leaves = db.relationship('Leave', backref='employee', lazy='dynamic', cascade="all, delete-orphan")
    assets = db.relationship('Asset', backref='assigned_employee', lazy='dynamic')

    def __repr__(self):
        return f'<EmployeeProfile {self.first_name} {self.last_name}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_in = db.Column(db.DateTime, default=datetime.utcnow)
    check_out = db.Column(db.DateTime, nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'))
    
    verification_method = db.Column(db.String(20), default='Manual') # Manual, Biometric
    verification_image = db.Column(db.String(100)) # Path to capture image

    def __repr__(self):
        return f'<Attendance {self.employee_id}>'

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    leave_type = db.Column(db.String(50), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    approved_by = db.Column(db.String(64))
    rejection_reason = db.Column(db.String(200))

    def __repr__(self):
        return f'<Leave {self.employee_id} from {self.start_date} to {self.end_date}>'

class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    
    # Earnings Breakdown
    basic = db.Column(db.Float, default=0.0)
    hra = db.Column(db.Float, default=0.0)
    conveyance = db.Column(db.Float, default=0.0)
    medical = db.Column(db.Float, default=0.0)
    special_allowance = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    incentives = db.Column(db.Float, default=0.0)
    reimbursements = db.Column(db.Float, default=0.0) # From Expenses
    
    # Deductions Breakdown
    pf = db.Column(db.Float, default=0.0)
    esi = db.Column(db.Float, default=0.0)
    professional_tax = db.Column(db.Float, default=0.0)
    tds = db.Column(db.Float, default=0.0)
    lop = db.Column(db.Float, default=0.0) # Loss of Pay Amount
    
    # Day Counts for Attendance
    days_in_month = db.Column(db.Integer, default=30)
    arrear_days = db.Column(db.Integer, default=0)
    lopr_days = db.Column(db.Integer, default=0)
    lop_days = db.Column(db.Integer, default=0)
    
    gross_salary = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default='Draft') # Draft, Processed, Paid
    generated_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payroll {self.employee_id} for {self.pay_period_end}>'

class SalaryStructure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False, unique=True)
    employee = db.relationship('EmployeeProfile', backref=db.backref('salary_structure', uselist=False))
    
    monthly_ctc = db.Column(db.Float, nullable=False)
    
    # Fixed Components
    basic = db.Column(db.Float, default=0.0)
    hra = db.Column(db.Float, default=0.0)
    conveyance = db.Column(db.Float, default=0.0)
    medical = db.Column(db.Float, default=0.0)
    special_allowance = db.Column(db.Float, default=0.0)
    
    # Standard Deductions
    pf = db.Column(db.Float, default=0.0)
    esi = db.Column(db.Float, default=0.0)
    professional_tax = db.Column(db.Float, default=0.0)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SalaryStructure for {self.employee_id}>'

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'CREATE', 'UPDATE', 'DELETE'
    resource_type = db.Column(db.String(50), nullable=False) # e.g., 'Employee', 'Payroll'
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True) # Description of what changed
    performed_by = db.Column(db.String(100), nullable=False) # User email or Name
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.resource_type} by {self.performed_by}>'

class JobOpening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    department = db.relationship('Department', backref='job_openings')
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Open') # Open, Closed, On Hold
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<JobOpening {self.title}>'

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    resume_file = db.Column(db.String(100)) # Path to resume
    status = db.Column(db.String(20), default='Applied') # Applied, Interviewing, Offered, Hired, Rejected
    job_id = db.Column(db.Integer, db.ForeignKey('job_opening.id'))
    job_opening = db.relationship('JobOpening', backref='candidates')
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Candidate {self.first_name} {self.last_name}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_no = db.Column(db.String(10), unique=True)
    description = db.Column(db.String(200), nullable=False)
    task_type = db.Column(db.String(20), nullable=False) # 'Onboarding', 'Offboarding', 'Others'
    other_type_name = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Assigned') # Assigned, WIP, Completed
    priority = db.Column(db.String(20), default='Low') # 'Low', 'Medium', 'High'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    assigned_role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True) # Who is responsible? e.g., Admin, IT
    assigned_role = db.relationship('Role')
    
    task_add_to_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=True)
    task_add_to = db.relationship('EmployeeProfile')
    
    target_date = db.Column(db.Date, nullable=True)
    
    instances = db.relationship('EmployeeTask', backref='master_task', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Task {self.task_no} - {self.description}>'

class EmployeeTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    employee = db.relationship('EmployeeProfile', backref='assigned_tasks')
    
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    # master_task backref via Task.instances
    
    status = db.Column(db.String(20), default='YTS') # YTS, WIP, Completed, Rejected
    reason = db.Column(db.Text)
    followup_date = db.Column(db.Date)
    
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_notified = db.Column(db.Boolean, default=False)
    
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<EmployeeTask {self.task_id} for {self.employee_id}>'

class Appraisal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    employee = db.relationship('EmployeeProfile', foreign_keys=[employee_id], backref='appraisals')
    
    reviewer_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=True)
    reviewer = db.relationship('EmployeeProfile', foreign_keys=[reviewer_id])
    
    period = db.Column(db.String(50), nullable=False) # e.g., "2025 Q1", "2024 Annual"
    appraisal_date = db.Column(db.Date, default=datetime.utcnow)
    
    score = db.Column(db.Integer) # 1-5 or 1-10
    feedback = db.Column(db.Text)
    goals = db.Column(db.Text) # Next period goals
    
    status = db.Column(db.String(20), default='Draft') # Draft, Submitted, Finalized

    def __repr__(self):
        return f'<Appraisal {self.employee_id} - {self.period}>'

class ExpenseClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    employee = db.relationship('EmployeeProfile', backref='expenses')
    
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False) # e.g. Travel, Food, Supplies
    date_occurred = db.Column(db.Date, nullable=False)
    
    receipt_file = db.Column(db.String(100)) # Path to uploaded receipt
    
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected, Paid
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    approved_by = db.Column(db.String(100))
    rejection_reason = db.Column(db.String(200))

    def __repr__(self):
        return f'<ExpenseClaim {self.title} for {self.employee_id}>'

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False, unique=True)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Holiday {self.name} on {self.date}>'

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    posted_by = db.Column(db.String(100))

    def __repr__(self):
        return f'<Announcement {self.title}>'

class EmployeeDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    employee = db.relationship('EmployeeProfile', backref='documents')
    
    title = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50)) # e.g. ID Proof, Contract, Offer Letter
    file_path = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<EmployeeDocument {self.title} for {self.employee_id}>'

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('employee_profile.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('EmployeeProfile', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('EmployeeProfile', foreign_keys=[recipient_id], backref='received_messages')

    def __repr__(self):
        return f'<ChatMessage from {self.sender_id} to {self.recipient_id}>'