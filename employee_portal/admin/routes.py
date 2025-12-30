from functools import wraps
from flask import render_template, flash, redirect, url_for, request, jsonify, make_response, send_from_directory, send_file, current_app
from flask_login import current_user
from sqlalchemy import extract, text
from werkzeug.utils import secure_filename
import os
import shutil
import zipfile
import tempfile
from . import bp
from employee_portal.models import User, EmployeeProfile, Attendance, Leave, Designation, Payroll, Asset, Vendor, Role, Department, AuditLog, JobOpening, Candidate, Task, EmployeeTask, Appraisal, ExpenseClaim, Holiday, Announcement, EmployeeDocument, AssetHistory, Credit, Debit, Invoice, PurchaseOrder, AuthorizedSignature, ShiftSchedule, BillEstimate
from datetime import date, datetime, timedelta
from employee_portal import db, csrf
from employee_portal.auth.forms import AdminAddEmployeeForm, AdminEditEmployeeForm, DesignationForm, PayrollForm, AdminChangeUserRoleForm, AssetForm, VendorForm, RoleForm, DepartmentForm, JobOpeningForm, CandidateForm, TaskForm, AppraisalForm, HolidayForm, AnnouncementForm, EmployeeDocumentForm, CreditForm, DebitForm, InvoiceForm, PurchaseOrderForm, AuthorizedSignatureForm, ShiftForm, BillEstimationForm, LetterHeadForm
from employee_portal.utils.helpers import save_picture, log_audit, save_file
from employee_portal.excel import export_assets_to_excel, export_vendors_to_excel, export_employees_to_excel, generate_employee_template, generate_holiday_template, generate_asset_template
from employee_portal.pdf import generate_transactions_pdf, generate_bill_estimate_pdf, generate_letter_head_pdf
import pandas as pd
import json
import random

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
            
        # Allow if Admin, Director
        if current_user.role in ['admin', 'director']:
            return f(*args, **kwargs)
            
        # Allow if user has ANY of the admin permissions
        admin_permissions = [
            'dashboard', 'checklist', 'view_employees', 'add_employee', 
            'designations', 'attendance', 'roles', 'change_role', 
            'view_assets', 'add_asset', 'view_vendors', 'add_vendor', 
            'manage_payroll', 'manage_ats'
        ]
        
        for perm in admin_permissions:
            if current_user.has_permission(perm):
                return f(*args, **kwargs)
            
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.index'))
    return decorated_function

@bp.route('/admin/audit_logs')
@admin_required
def audit_logs():
    # Auto-cleanup: Delete logs older than 7 days
    retention_cutoff = datetime.utcnow() - timedelta(days=7)
    try:
        AuditLog.query.filter(AuditLog.timestamp < retention_cutoff).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log error to console but don't crash the page for the user
        print(f"Audit Log Cleanup Error: {e}")

    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()
    date_filter = request.args.get('date', '').strip()
    user_filter = request.args.get('user', '').strip()

    query = AuditLog.query

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AuditLog.timestamp) == target_date)
        except ValueError:
            pass
    if user_filter:
        query = query.filter(AuditLog.performed_by.ilike(f'%{user_filter}%'))

    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=10)
    
    # Get unique actions for the filter dropdown
    actions = db.session.query(AuditLog.action).distinct().all()
    action_list = [a[0] for a in actions]

    return render_template('admin/audit_logs.html', 
                           logs=logs, 
                           title='Audit Logs', 
                           action_filter=action_filter, 
                           date_filter=date_filter, 
                           user_filter=user_filter,
                           action_list=action_list)

@bp.route('/admin/api/employees/search')
@admin_required
def search_employees_api():
    query_str = request.args.get('q', '').strip()
    if not query_str:
        return jsonify([])
    
    query = EmployeeProfile.query.join(User).join(Role).filter(
        db.or_(
            EmployeeProfile.first_name.ilike(f'%{query_str}%'),
            EmployeeProfile.last_name.ilike(f'%{query_str}%'),
            User.employeeid.ilike(f'%{query_str}%'),
            Role.name.ilike(f'%{query_str}%'),
            db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name).ilike(f'%{query_str}%')
        )
    ).limit(10)
    
    results = []
    for emp in query.all():
        role_name = emp.user.user_role.name if emp.user.user_role else 'No Role'
        results.append(f"{emp.first_name} {emp.last_name} ({emp.user.employeeid}) - {role_name}")
    
    return jsonify(results)

@bp.route('/admin/api/vendor_details/<string:name>')
@admin_required
def get_vendor_details(name):
    if name == 'Gentize':
        return jsonify({'name': 'Gentize', 'contact': 'Internal Asset', 'email': '-', 'phone': '-'})
    
    vendor = Vendor.query.filter_by(name=name).first()
    if vendor:
        return jsonify({
            'name': vendor.name,
            'contact': vendor.contact_person,
            'email': vendor.email,
            'phone': vendor.phone
        })
    return jsonify({})

@bp.route('/admin/dashboard')
@admin_required
def dashboard():
    from employee_portal.models import Announcement
    today = date.today()
    
    total_employees = EmployeeProfile.query.count()
    present_today = db.session.query(Attendance.employee_id).filter(db.func.date(Attendance.check_in) == today).distinct().count()
    
    leave_today = Leave.query.filter(
        Leave.status == 'Approved',
        Leave.start_date <= today,
        Leave.end_date >= today
    ).count()
    
    assets_count = Asset.query.count()
    vendors_count = Vendor.query.count()
    approvals_count = Leave.query.filter_by(status='Pending').count()
    
    birthdays_count = EmployeeProfile.query.filter(
        extract('month', EmployeeProfile.date_of_birth) == today.month,
        extract('day', EmployeeProfile.date_of_birth) == today.day
    ).count()
    
    # Count pending expense claims
    expense_count = ExpenseClaim.query.filter_by(status='Pending').count()
    
    # Count pending tasks
    pending_task_count = EmployeeTask.query.filter(EmployeeTask.status != 'Completed').count()
    
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.date_posted.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                           total_employees=total_employees, 
                           present_today=present_today, 
                           leave_today=leave_today,
                           assets_count=assets_count,
                           vendors_count=vendors_count,
                           approvals_count=approvals_count,
                           birthdays_count=birthdays_count,
                           expense_count=expense_count,
                           pending_task_count=pending_task_count,
                           announcements=announcements,
                           today=today)

@bp.route('/admin/present_today')
@admin_required
def present_today():
    today = date.today()
    present_employee_ids = db.session.query(Attendance.employee_id).filter(db.func.date(Attendance.check_in) == today).distinct().all()
    present_employees = EmployeeProfile.query.filter(EmployeeProfile.id.in_([emp_id for emp_id, in present_employee_ids])).all()
    return render_template('admin/present_today.html', employees=present_employees, title="Employees Present Today")

@bp.route('/admin/on_leave_today')
@admin_required
def on_leave_today():
    today = date.today()
    leave_employee_ids = db.session.query(Leave.employee_id).filter(
        db.and_(
            Leave.start_date <= today, 
            Leave.end_date >= today,
            Leave.status == 'Approved'
        )
    ).distinct().all()
    
    leave_ids = [emp_id for emp_id, in leave_employee_ids]
    employees_on_leave = EmployeeProfile.query.filter(EmployeeProfile.id.in_(leave_ids)).all()
    
    return render_template('admin/on_leave_today.html', employees=employees_on_leave, title="Employees on Leave Today")

@bp.route('/admin/employees')
@admin_required
def view_employees():
    search_query = request.args.get('search_query', '')
    query = EmployeeProfile.query.join(User).join(Role).filter(Role.name != 'Admin')

    if search_query:
        term = search_query.strip()
        query = query.filter(
            db.or_(
                EmployeeProfile.first_name.ilike(f'%{term}%'),
                EmployeeProfile.last_name.ilike(f'%{term}%'),
                User.employeeid.ilike(f'%{term}%'),
                Role.name.ilike(f'%{term}%'),
                db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name).ilike(f'%{term}%'),
                db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name, ' (', User.employeeid, ')').ilike(f'%{term}%')
            )
        )
    
    employees = query.all()
    return render_template('admin/view_employees.html', employees=employees, search_query=search_query)

def generate_employee_id():
    last_user = User.query.filter(User.employeeid.like('GEN%')).order_by(User.id.desc()).first()
    if last_user and len(last_user.employeeid) >= 7:
        try:
            last_id = int(last_user.employeeid[3:])
            return f"GEN{last_id + 1:04d}"
        except ValueError:
            return "GEN0001"
    else:
        return "GEN0001"

@bp.route('/admin/add_employee', methods=['GET', 'POST'])
@admin_required
def add_employee():
    form = AdminAddEmployeeForm()
    if form.validate_on_submit():
        new_employee_id = generate_employee_id()
        
        # Determine Role based on Designation
        if form.designation.data and form.designation.data.role:
            user_role = form.designation.data.role
        else:
            # Fallback to Employee role
            user_role = Role.query.filter_by(name='Employee').first()
            if not user_role:
                 flash('Error: Default "Employee" role not found.', 'danger')
                 return render_template('admin/add_employee.html', form=form)

        user = User(employeeid=new_employee_id, email=form.email.data, user_role=user_role)
        user.set_password(form.password.data)
        
        profile = EmployeeProfile(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            prefix=form.prefix.data,
            gender=form.gender.data,
            marital_status=form.marital_status.data,
            phone_number=form.phone_number.data,
            address=form.address.data,
            date_of_birth=form.date_of_birth.data,
            pan_number=form.pan_number.data,
            aadhar_number=form.aadhar_number.data,
            uan_number=form.uan_number.data,
            pf_number=form.pf_number.data,
            esi_number=form.esi_number.data,
            emergency_contact=form.emergency_contact.data,
            bank_account_number=form.bank_account_number.data,
            bank_name=form.bank_name.data,
            ifsc_code=form.ifsc_code.data,
            branch=form.branch.data,
            date_of_joining=form.date_of_joining.data,
            department=form.department.data,
            designation=form.designation.data,
            manager=form.reports_to.data,
            previous_employer=form.previous_employer.data,
            years_of_experience=form.years_of_experience.data,
            employment_type=form.employment_type.data,
            is_resigned=form.is_resigned.data,
            notice_period=form.notice_period.data,
            resigned_date=form.resigned_date.data,
            user=user
        )
        
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            profile.image_file = picture_file
        
        db.session.add(user)
        db.session.add(profile)
        db.session.commit() # Commit first to get ID
        
        # Assign Onboarding Tasks
        onboarding_tasks = Task.query.filter_by(task_type='Onboarding').all()
        for task in onboarding_tasks:
            emp_task = EmployeeTask(employee_id=profile.id, task_id=task.id)
            db.session.add(emp_task)
        db.session.commit()

        log_audit('CREATE', 'Employee', user.id, f"Onboarded employee {new_employee_id}", current_user)
        flash(f'Employee {new_employee_id} added successfully.', 'success')
        return redirect(url_for('admin.view_employees'))
    
    return render_template('admin/add_employee.html', form=form)

@bp.route('/admin/employee/<int:employee_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_employee(employee_id):
    employee_profile = EmployeeProfile.query.get_or_404(employee_id)
    user = employee_profile.user
    
    form = AdminEditEmployeeForm(original_user_id=user.id)
    
    if form.validate_on_submit():
        user.employeeid = form.employeeid.data
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
            
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            employee_profile.image_file = picture_file
            
        employee_profile.first_name = form.first_name.data
        employee_profile.last_name = form.last_name.data
        employee_profile.email = form.email.data
        employee_profile.prefix = form.prefix.data
        employee_profile.gender = form.gender.data
        employee_profile.marital_status = form.marital_status.data
        employee_profile.phone_number = form.phone_number.data
        employee_profile.address = form.address.data
        employee_profile.date_of_birth = form.date_of_birth.data
        employee_profile.pan_number = form.pan_number.data
        employee_profile.aadhar_number = form.aadhar_number.data
        employee_profile.uan_number = form.uan_number.data
        employee_profile.pf_number = form.pf_number.data
        employee_profile.esi_number = form.esi_number.data
        employee_profile.emergency_contact = form.emergency_contact.data
        employee_profile.bank_account_number = form.bank_account_number.data
        employee_profile.bank_name = form.bank_name.data
        employee_profile.ifsc_code = form.ifsc_code.data
        employee_profile.branch = form.branch.data
        employee_profile.department = form.department.data
        employee_profile.designation = form.designation.data
        
        # Auto-update Role based on Designation
        if form.designation.data and form.designation.data.role:
            user.user_role = form.designation.data.role
            
        employee_profile.manager = form.reports_to.data
        employee_profile.previous_employer = form.previous_employer.data
        employee_profile.years_of_experience = form.years_of_experience.data
        employee_profile.employment_type = form.employment_type.data
        employee_profile.date_of_joining = form.date_of_joining.data
        
        # Check if resignation status changed to True
        was_resigned = employee_profile.is_resigned
        employee_profile.is_resigned = form.is_resigned.data
        employee_profile.notice_period = form.notice_period.data
        
        if form.is_resigned.data and not form.resigned_date.data:
            employee_profile.resigned_date = date.today()
        else:
            employee_profile.resigned_date = form.resigned_date.data
            
        if not was_resigned and employee_profile.is_resigned:
            # Trigger Offboarding Tasks
            offboarding_tasks = Task.query.filter_by(task_type='Offboarding').all()
            for task in offboarding_tasks:
                # Check if already assigned to avoid duplicates (though unlikely in this flow)
                exists = EmployeeTask.query.filter_by(employee_id=employee_profile.id, task_id=task.id).first()
                if not exists:
                    emp_task = EmployeeTask(employee_id=employee_profile.id, task_id=task.id)
                    db.session.add(emp_task)
        
        db.session.commit()
        log_audit('UPDATE', 'Employee', employee_profile.id, f"Updated profile for {user.employeeid}", current_user)
        flash('Employee profile updated successfully!', 'success')
        return redirect(url_for('admin.view_employees'))
        
    elif request.method == 'GET':
        form.employeeid.data = user.employeeid
        form.email.data = user.email
        form.first_name.data = employee_profile.first_name
        form.last_name.data = employee_profile.last_name
        form.prefix.data = employee_profile.prefix
        form.gender.data = employee_profile.gender
        form.marital_status.data = employee_profile.marital_status
        form.phone_number.data = employee_profile.phone_number
        form.address.data = employee_profile.address
        form.date_of_birth.data = employee_profile.date_of_birth
        form.pan_number.data = employee_profile.pan_number
        form.aadhar_number.data = employee_profile.aadhar_number
        form.uan_number.data = employee_profile.uan_number
        form.pf_number.data = employee_profile.pf_number
        form.esi_number.data = employee_profile.esi_number
        form.emergency_contact.data = employee_profile.emergency_contact
        form.bank_account_number.data = employee_profile.bank_account_number
        form.bank_name.data = employee_profile.bank_name
        form.ifsc_code.data = employee_profile.ifsc_code
        form.branch.data = employee_profile.branch
        form.department.data = employee_profile.department
        form.designation.data = employee_profile.designation
        form.reports_to.data = employee_profile.manager
        form.previous_employer.data = employee_profile.previous_employer
        form.years_of_experience.data = employee_profile.years_of_experience
        form.employment_type.data = employee_profile.employment_type
        form.date_of_joining.data = employee_profile.date_of_joining
        form.is_resigned.data = employee_profile.is_resigned
        form.notice_period.data = employee_profile.notice_period
        form.resigned_date.data = employee_profile.resigned_date

    return render_template('admin/edit_employee.html', form=form, employee_profile=employee_profile, title='Edit Employee')

@bp.route('/admin/designations', methods=['GET', 'POST'])
@admin_required
def designations():
    form = DesignationForm()
    if form.validate_on_submit():
        designation = Designation(title=form.title.data, role=form.role.data)
        db.session.add(designation)
        db.session.commit()
        flash('Designation added.', 'success')
        return redirect(url_for('admin.designations'))
    
    designations = Designation.query.all()
    return render_template('admin/designations.html', form=form, designations=designations, title='Manage Designations')

@bp.route('/admin/designations/<int:designation_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_designation(designation_id):
    designation = Designation.query.get_or_404(designation_id)
    form = DesignationForm()
    if form.validate_on_submit():
        designation.title = form.title.data
        designation.role = form.role.data
        db.session.commit()
        flash('Designation updated.', 'success')
        return redirect(url_for('admin.designations'))
    elif request.method == 'GET':
        form.title.data = designation.title
        form.role.data = designation.role
    return render_template('admin/edit_designation.html', form=form, title='Edit Designation')

@bp.route('/admin/designations/<int:designation_id>/delete', methods=['POST'])
@admin_required
def delete_designation(designation_id):
    designation = Designation.query.get_or_404(designation_id)
    db.session.delete(designation)
    db.session.commit()
    flash('Designation deleted.', 'success')
    return redirect(url_for('admin.designations'))

from employee_portal.models import User, EmployeeProfile, Attendance, Leave, Designation, Payroll, Asset, Vendor, Role, Department, AuditLog, JobOpening, Candidate, Task, EmployeeTask, Appraisal, ExpenseClaim, Holiday, Announcement, EmployeeDocument, AssetHistory, SalaryStructure
# ... imports
from employee_portal.auth.forms import AdminAddEmployeeForm, AdminEditEmployeeForm, DesignationForm, PayrollForm, AdminChangeUserRoleForm, AssetForm, VendorForm, RoleForm, DepartmentForm, JobOpeningForm, CandidateForm, TaskForm, AppraisalForm, HolidayForm, AnnouncementForm, EmployeeDocumentForm, SalaryStructureForm

# ... routes

@bp.route('/admin/payroll/structure', methods=['GET', 'POST'])
@admin_required
def salary_structures():
    form = SalaryStructureForm()
    if form.validate_on_submit():
        structure = SalaryStructure.query.filter_by(employee_id=form.employee.data.id).first()
        if not structure:
            structure = SalaryStructure(employee_id=form.employee.data.id)
            db.session.add(structure)
        
        structure.monthly_ctc = form.monthly_ctc.data
        structure.basic = form.basic.data
        structure.hra = form.hra.data
        structure.conveyance = form.conveyance.data
        structure.medical = form.medical.data
        structure.special_allowance = form.special_allowance.data
        structure.pf = form.pf.data
        structure.esi = form.esi.data
        structure.professional_tax = form.professional_tax.data
        
        db.session.commit()
        log_audit('UPDATE', 'SalaryStructure', structure.id, f"Updated salary structure for {form.employee.data.first_name}", current_user)
        flash('Salary structure updated.', 'success')
        return redirect(url_for('admin.salary_structures'))
    
    structures = SalaryStructure.query.all()
    return render_template('admin/manage_structures.html', form=form, structures=structures, title='Salary Structures')

@bp.route('/admin/payroll/structure/<int:structure_id>/delete', methods=['POST'])
@admin_required
def delete_salary_structure(structure_id):
    structure = SalaryStructure.query.get_or_404(structure_id)
    db.session.delete(structure)
    db.session.commit()
    log_audit('DELETE', 'SalaryStructure', structure_id, f"Deleted salary structure for {structure.employee.first_name}", current_user)
    flash('Salary structure deleted.', 'success')
    return redirect(url_for('admin.salary_structures'))

@bp.route('/admin/api/payroll/prefill/<int:employee_id>')
@admin_required
def api_prefill_payroll(employee_id):
    from employee_portal.models import SalaryStructure, ExpenseClaim, Attendance, Leave, EmployeeProfile
    from datetime import date, datetime
    import calendar
    
    employee = EmployeeProfile.query.get_or_404(employee_id)
    structure = SalaryStructure.query.filter_by(employee_id=employee_id).first()
    if not structure:
        return jsonify({'error': 'No structure found'})
    
    # Target month and year
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    # Total days in the month
    days_in_month = calendar.monthrange(year, month)[1]
    net_worked_days = float(days_in_month)
    
    # If resigned, calculate worked days in the final month
    if employee.is_resigned and employee.resigned_date:
        if employee.resigned_date.year == year and employee.resigned_date.month == month:
            # worked until resigned_date
            net_worked_days = float(employee.resigned_date.day)
    
    # Calculate pro-rated factor
    factor = net_worked_days / float(days_in_month)
    
    # Calculate Reimbursements
    reimbursements = db.session.query(db.func.sum(ExpenseClaim.amount)).filter(
        ExpenseClaim.employee_id == employee_id,
        ExpenseClaim.status == 'Approved'
    ).scalar() or 0.0
    
    return jsonify({
        'basic': round(structure.basic * factor, 2),
        'hra': round(structure.hra * factor, 2),
        'conveyance': round(structure.conveyance * factor, 2),
        'medical': round(structure.medical * factor, 2),
        'special_allowance': round(structure.special_allowance * factor, 2),
        'pf': round(structure.pf * factor, 2),
        'esi': round(structure.esi * factor, 2),
        'professional_tax': structure.professional_tax, # Usually fixed
        'reimbursements': reimbursements,
        'days_in_month': days_in_month,
        'net_worked_days': net_worked_days
    })

@bp.route('/admin/payroll/release_offer', methods=['GET', 'POST'])
@admin_required
def release_offer():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        if not employee_id:
            flash('Please select an employee.', 'warning')
            return redirect(url_for('admin.release_offer'))
            
        employee = EmployeeProfile.query.get_or_404(employee_id)
        salary_structure = SalaryStructure.query.filter_by(employee_id=employee.id).first()
        
        # Generate PDF
        from employee_portal.pdf import generate_offer_letter_pdf
        pdf_filename = generate_offer_letter_pdf(employee, salary_structure)
        
        # Check if an offer letter already exists for this employee
        existing_doc = EmployeeDocument.query.filter_by(
            employee_id=employee.id, 
            document_type="Offer Letter"
        ).first()

        if existing_doc:
            # Update existing record
            existing_doc.upload_date = datetime.utcnow()
            doc_id = existing_doc.id
        else:
            # Save new to Documents
            doc = EmployeeDocument(
                title="Offer Letter",
                document_type="Offer Letter",
                file_path=pdf_filename,
                employee_id=employee.id
            )
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id
        
        db.session.commit()
        
        log_audit('CREATE' if not existing_doc else 'UPDATE', 'OfferLetter', doc_id, f"Released offer letter for {employee.first_name}", current_user)
        flash(f'Offer letter generated and released for {employee.first_name}.', 'success')
        return redirect(url_for('admin.release_offer'))
    
    # GET: List employees
    employees = EmployeeProfile.query.join(User).filter(EmployeeProfile.is_resigned == False).all()
    
    # Check for existing offer letters
    existing_offers = EmployeeDocument.query.filter_by(document_type='Offer Letter').all()
    offer_map = {doc.employee_id: doc for doc in existing_offers}

    return render_template('admin/release_offer.html', employees=employees, offer_map=offer_map, title='Release Offer Letter')

@bp.route('/admin/payroll', methods=['GET', 'POST'])
@admin_required
def manage_payroll():
    form = PayrollForm()
    if form.validate_on_submit():
        # ... (keep existing creation logic)
        gross = form.basic.data + form.hra.data + form.conveyance.data + \
                form.medical.data + form.special_allowance.data + \
                form.bonus.data + form.incentives.data + form.reimbursements.data
        deductions = form.pf.data + form.esi.data + form.professional_tax.data + \
                     form.tds.data + form.lop.data
        net = gross - deductions
        payroll = Payroll(
            employee_id=form.employee.data.id,
            pay_period_start=form.pay_period_start.data,
            pay_period_end=form.pay_period_end.data,
            basic=form.basic.data,
            hra=form.hra.data,
            conveyance=form.conveyance.data,
            medical=form.medical.data,
            special_allowance=form.special_allowance.data,
            bonus=form.bonus.data,
            incentives=form.incentives.data,
            reimbursements=form.reimbursements.data,
            pf=form.pf.data,
            esi=form.esi.data,
            professional_tax=form.professional_tax.data,
            tds=form.tds.data,
            lop=form.lop.data,
            days_in_month=int(form.days_in_month.data),
            arrear_days=int(form.arrear_days.data),
            lopr_days=int(form.lopr_days.data),
            lop_days=int(form.lop_days.data),
            gross_salary=gross,
            total_deductions=deductions,
            net_salary=net,
            status=form.status.data
        )
        if payroll.status in ['Processed', 'Paid']:
            # Find approved claims to pay
            claims_to_pay = ExpenseClaim.query.filter(
                ExpenseClaim.employee_id == payroll.employee_id, 
                ExpenseClaim.status == 'Approved'
            ).all()
            
            for claim in claims_to_pay:
                claim.status = 'Paid'
                # Create Debit Record
                debit = Debit(
                    date=date.today(),
                    amount=claim.amount,
                    description=f"Payroll Expense: {claim.title} - {claim.employee.first_name} {claim.employee.last_name}",
                    category='Expense Claim',
                    payment_mode='Bank Transfer',
                    reference_number=f"EXP-{claim.id}"
                )
                db.session.add(debit)
            
            # If Paid, record Salary Debit
            if payroll.status == 'Paid':
                salary_debit = Debit(
                    date=date.today(),
                    amount=payroll.net_salary,
                    description=f"Salary Payment: {payroll.employee.first_name} {payroll.employee.last_name} ({payroll.pay_period_end.strftime('%b %Y')})",
                    category='Salary',
                    payment_mode='Bank Transfer',
                    reference_number=f"SAL-{payroll.employee.id}-{payroll.pay_period_end.strftime('%m%Y')}"
                )
                db.session.add(salary_debit)

        db.session.add(payroll)
        db.session.commit()
        log_audit('CREATE', 'Payroll', payroll.id, f"Generated payroll for {form.employee.data.first_name}", current_user)
        flash('Payroll record created successfully.', 'success')
        return redirect(url_for('admin.manage_payroll'))
    
    # Filtering Logic
    filter_year = request.args.get('year', date.today().year, type=int)
    filter_month = request.args.get('month', date.today().month, type=int)
    
    payrolls = Payroll.query.filter(
        extract('year', Payroll.pay_period_end) == filter_year,
        extract('month', Payroll.pay_period_end) == filter_month
    ).order_by(Payroll.generated_date.desc()).all()
    
    return render_template('admin/manage_payroll.html', form=form, payrolls=payrolls, filter_year=filter_year, filter_month=filter_month, title='Manage Payroll')

@bp.route('/admin/payroll/bulk_generate', methods=['POST'])
@admin_required
def bulk_generate_payroll():
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    
    if not month or not year:
        flash('Please select month and year for bulk generation.', 'danger')
        return redirect(url_for('admin.manage_payroll'))
        
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
        
    days_in_month = end_date.day
    
    employees_with_structure = SalaryStructure.query.all()
    count = 0
    
    for structure in employees_with_structure:
        # Check if payroll already exists for this period
        existing = Payroll.query.filter_by(employee_id=structure.employee_id, pay_period_end=end_date).first()
        if existing:
            continue
            
        # Calculate reimbursements
        reimbursements = db.session.query(db.func.sum(ExpenseClaim.amount)).filter(
            ExpenseClaim.employee_id == structure.employee_id,
            ExpenseClaim.status == 'Approved'
        ).scalar() or 0.0
        
        gross = structure.basic + structure.hra + structure.conveyance + \
                structure.medical + structure.special_allowance + reimbursements
        
        deductions = structure.pf + structure.esi + structure.professional_tax
        
        payroll = Payroll(
            employee_id=structure.employee_id,
            pay_period_start=start_date,
            pay_period_end=end_date,
            basic=structure.basic,
            hra=structure.hra,
            conveyance=structure.conveyance,
            medical=structure.medical,
            special_allowance=structure.special_allowance,
            reimbursements=reimbursements,
            pf=structure.pf,
            esi=structure.esi,
            professional_tax=structure.professional_tax,
            gross_salary=gross,
            total_deductions=deductions,
            net_salary=gross - deductions,
            days_in_month=days_in_month,
            status='Draft'
        )
        db.session.add(payroll)
        count += 1
        
    db.session.commit()
    log_audit('BULK_CREATE', 'Payroll', None, f"Bulk generated {count} payroll drafts for {end_date.strftime('%B %Y')}", current_user)
    flash(f'Successfully generated {count} payroll drafts.', 'success')
    return redirect(url_for('admin.manage_payroll', year=year, month=month))

@bp.route('/admin/payroll/bulk_status/<string:status>', methods=['POST'])
@admin_required
def bulk_update_payroll_status(status):
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    
    if not month or not year:
        flash('Select period for bulk update.', 'danger')
        return redirect(url_for('admin.manage_payroll'))

    # Update all matching records that are NOT already in that status
    # First, get the records to process logic if needed
    payrolls_to_update = Payroll.query.filter(
        extract('year', Payroll.pay_period_end) == year,
        extract('month', Payroll.pay_period_end) == month,
        Payroll.status != status
    ).all()
    
    updated_count = 0
    for p in payrolls_to_update:
        p.status = status
        updated_count += 1
        
        # If marking as Paid, create Salary Debit
        if status == 'Paid':
            salary_debit = Debit(
                date=date.today(),
                amount=p.net_salary,
                description=f"Salary Payment (Bulk): {p.employee.first_name} {p.employee.last_name} ({p.pay_period_end.strftime('%b %Y')})",
                category='Salary',
                payment_mode='Bank Transfer',
                reference_number=f"SAL-{p.employee.id}-{p.pay_period_end.strftime('%m%Y')}"
            )
            db.session.add(salary_debit)
            
            # Also handle expense claims for this employee
            claims_to_pay = ExpenseClaim.query.filter(
                ExpenseClaim.employee_id == p.employee_id,
                ExpenseClaim.status == 'Approved'
            ).all()
            
            for claim in claims_to_pay:
                claim.status = 'Paid'
                # Create Debit Record
                debit = Debit(
                    date=date.today(),
                    amount=claim.amount,
                    description=f"Payroll Expense (Bulk): {claim.title} - {claim.employee.first_name} {claim.employee.last_name}",
                    category='Expense Claim',
                    payment_mode='Bank Transfer',
                    reference_number=f"EXP-{claim.id}"
                )
                db.session.add(debit)

    db.session.commit()
    log_audit('BULK_UPDATE', 'Payroll', None, f"Bulk updated {updated_count} records to {status} for {month}/{year}", current_user)
    flash(f'Bulk updated {updated_count} payroll records to {status}.', 'success')
    return redirect(url_for('admin.manage_payroll', year=year, month=month))

@bp.route('/admin/payroll/<int:payroll_id>/status/<string:status>', methods=['POST'])
@admin_required
def update_payroll_status(payroll_id, status):
    payroll = Payroll.query.get_or_404(payroll_id)
    old_status = payroll.status
    payroll.status = status
    
    # If moving to Paid, create Debit(s)
    if status == 'Paid' and old_status != 'Paid':
        # Salary Debit
        salary_debit = Debit(
            date=date.today(),
            amount=payroll.net_salary,
            description=f"Salary Payment: {payroll.employee.first_name} {payroll.employee.last_name} ({payroll.pay_period_end.strftime('%b %Y')})",
            category='Salary',
            payment_mode='Bank Transfer',
            reference_number=f"SAL-{payroll.employee.id}-{payroll.pay_period_end.strftime('%m%Y')}"
        )
        db.session.add(salary_debit)
        
        # Expense Claims
        claims_to_pay = ExpenseClaim.query.filter(
            ExpenseClaim.employee_id == payroll.employee_id, 
            ExpenseClaim.status == 'Approved'
        ).all()
        
        for claim in claims_to_pay:
            claim.status = 'Paid'
            # Create Debit Record
            debit = Debit(
                date=date.today(),
                amount=claim.amount,
                description=f"Payroll Expense: {claim.title} - {claim.employee.first_name} {claim.employee.last_name}",
                category='Expense Claim',
                payment_mode='Bank Transfer',
                reference_number=f"EXP-{claim.id}"
            )
            db.session.add(debit)
            
        flash('Payroll marked as Paid and Debit records created.', 'success')
    else:
        flash(f'Payroll marked as {status}.', 'info')
        
    db.session.commit()
    return redirect(url_for('admin.manage_payroll'))

@bp.route('/admin/change_role', methods=['GET', 'POST'])
@admin_required
def change_role():
    form = AdminChangeUserRoleForm()
    if form.validate_on_submit():
        user = User.query.get(form.user_id.data.id)
        user.user_role = form.role.data
        db.session.commit()
        flash(f'Role for {user.employeeid} updated to {user.user_role.name}!', 'success')
        return redirect(url_for('admin.change_role'))
    return render_template('admin/change_role.html', form=form, title='Change User Role')

@bp.route('/admin/employee/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_employee(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.role == 'admin': 
        flash('Cannot delete an admin user!', 'danger')
        return redirect(url_for('admin.view_employees'))

    employee_profile = EmployeeProfile.query.filter_by(user_id=user_to_delete.id).first()
    emp_name = f"{employee_profile.first_name} {employee_profile.last_name}" if employee_profile else "Unknown"
    emp_id = user_to_delete.employeeid

    if employee_profile:
        db.session.delete(employee_profile)
    
    db.session.delete(user_to_delete)
    db.session.commit()
    
    log_audit('DELETE', 'Employee', user_id, f"Deleted employee {emp_name} ({emp_id})", current_user)
    
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('admin.view_employees'))

@bp.route('/admin/employee/<int:employee_id>/profile')
@admin_required
def admin_view_employee_profile(employee_id):
    employee_profile = EmployeeProfile.query.get_or_404(employee_id)
    image_file = url_for('static', filename='img/' + (employee_profile.image_file or 'default.jpg'))
    doc_form = EmployeeDocumentForm()
    return render_template('admin/_employee_profile_details.html', employee=employee_profile, title=f"{employee_profile.first_name}'s Profile", image_file=image_file, doc_form=doc_form)

# --- Asset Routes ---
# ... (Asset routes are here, no change needed)

# --- Vendor Routes ---
# ... (Vendor routes are here)

# --- Role Routes ---

@bp.route('/admin/roles')
@admin_required
def roles():
    roles = Role.query.all()
    return render_template('admin/roles.html', roles=roles, title='Manage Roles')

@bp.route('/admin/roles/add', methods=['GET', 'POST'])
@admin_required
def add_role():
    form = RoleForm()
    if form.validate_on_submit():
        role_name = form.name.data.title # Extract title string from Designation object
        permissions_str = ','.join(form.permissions.data)
        role = Role(name=role_name, permissions=permissions_str)
        db.session.add(role)
        db.session.commit()
        flash('Role added successfully.', 'success')
        return redirect(url_for('admin.roles'))
    return render_template('admin/add_role.html', form=form, title='Add Role')

@bp.route('/admin/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    form = RoleForm()
    if form.validate_on_submit():
        role.name = form.name.data.title # Extract title string from Designation object
        role.permissions = ','.join(form.permissions.data)
        db.session.commit()
        flash('Role updated successfully.', 'success')
        return redirect(url_for('admin.roles'))
    elif request.method == 'GET':
        # Find matching designation object for the role name string
        designation = Designation.query.filter_by(title=role.name).first()
        if designation:
            form.name.data = designation
        if role.permissions:
            form.permissions.data = role.permissions.split(',')
    return render_template('admin/add_role.html', form=form, title='Edit Role')

@bp.route('/admin/roles/<int:role_id>/delete', methods=['POST'])
@admin_required
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    # Check if role assigned to users?
    if role.users.count() > 0:
        flash('Cannot delete role assigned to users.', 'danger')
        return redirect(url_for('admin.roles'))
    db.session.delete(role)
    db.session.commit()
    flash('Role deleted.', 'success')
    return redirect(url_for('admin.roles'))

# --- Asset Routes ---

@bp.route('/admin/assets')
@admin_required
def view_assets():
    search_query = request.args.get('search_query', '')
    query = Asset.query
    if search_query:
        query = query.filter(
            db.or_(
                Asset.name.ilike(f'%{search_query}%'),
                Asset.serial_number.ilike(f'%{search_query}%')
            )
        )
    assets = query.all()
    return render_template('admin/view_assets.html', assets=assets, search_query=search_query, title='Manage Assets', today=date.today())

@bp.route('/admin/assets/add', methods=['GET', 'POST'])
@admin_required
def add_asset():
    active_tab = request.args.get('tab', 'individual')
    form = AssetForm()
    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data,
            brand=form.brand.data,
            model_name=form.model_name.data,
            category=form.category.data,
            serial_number=form.serial_number.data,
            condition=form.condition.data,
            status=form.status.data,
            purchase_date=form.purchase_date.data,
            purchase_cost=form.purchase_cost.data,
            warranty_expiry=form.warranty_expiry.data,
            vendor_id=form.vendor.data.id if form.vendor.data else None,
            owned_by=form.vendor.data.name if form.vendor.data else 'Gentize',
            assigned_to_id=form.assigned_to.data.id if form.assigned_to.data else None
        )
        db.session.add(asset)
        try:
            db.session.commit()
            
            # Initial History Log
            history = AssetHistory(
                asset_id=asset.id,
                employee_id=asset.assigned_to_id,
                action='Created',
                notes=f"Asset initialized with status: {asset.status}",
                performed_by=current_user.email
            )
            db.session.add(history)
            db.session.commit()
            
            log_audit('CREATE', 'Asset', asset.id, f"Added asset {asset.name} ({asset.serial_number})", current_user)
            flash('Asset added successfully.', 'success')
            return redirect(url_for('admin.view_assets'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding asset: {str(e)}', 'danger')
            
    return render_template('admin/add_asset.html', form=form, title='Add Asset', active_tab=active_tab)

@bp.route('/admin/assets/<int:asset_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    form = AssetForm()
    
    if form.validate_on_submit():
        # Check if assignment changed
        old_assignee_id = asset.assigned_to_id
        new_assignee_id = form.assigned_to.data.id if form.assigned_to.data else None
        
        asset.name = form.name.data
        asset.brand = form.brand.data
        asset.model_name = form.model_name.data
        asset.category = form.category.data
        asset.serial_number = form.serial_number.data
        asset.condition = form.condition.data
        asset.status = form.status.data
        asset.purchase_date = form.purchase_date.data
        asset.purchase_cost = form.purchase_cost.data
        asset.warranty_expiry = form.warranty_expiry.data
        asset.vendor_id = form.vendor.data.id if form.vendor.data else None
        asset.owned_by = form.vendor.data.name if form.vendor.data else 'Gentize'
        asset.assigned_to_id = new_assignee_id
        
        try:
            # If assignment changed, log it
            if old_assignee_id != new_assignee_id:
                action = 'Assigned' if new_assignee_id else 'Returned'
                history = AssetHistory(
                    asset_id=asset.id,
                    employee_id=new_assignee_id,
                    action=action,
                    notes=f"Status: {asset.status}",
                    performed_by=current_user.email
                )
                db.session.add(history)
            
            db.session.commit()
            log_audit('UPDATE', 'Asset', asset.id, f"Updated asset {asset.name}", current_user)
            flash('Asset updated successfully.', 'success')
            return redirect(url_for('admin.view_assets'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating asset: {str(e)}', 'danger')
            
    elif request.method == 'GET':
        form.name.data = asset.name
        form.brand.data = asset.brand
        form.model_name.data = asset.model_name
        form.category.data = asset.category
        form.serial_number.data = asset.serial_number
        form.condition.data = asset.condition
        form.status.data = asset.status
        form.purchase_date.data = asset.purchase_date
        form.purchase_cost.data = asset.purchase_cost
        form.warranty_expiry.data = asset.warranty_expiry
        
        from employee_portal.models import Vendor, EmployeeProfile
        if asset.vendor_id:
            form.vendor.data = Vendor.query.get(asset.vendor_id)
        if asset.assigned_to_id:
            form.assigned_to.data = EmployeeProfile.query.get(asset.assigned_to_id)
        
    return render_template('admin/add_asset.html', form=form, title='Edit Asset')

@bp.route('/admin/assets/<int:asset_id>/view')
@admin_required
def view_asset_details(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    history = asset.history.order_by(AssetHistory.date_action.desc()).all()
    return render_template('admin/view_asset_details.html', asset=asset, history=history, title=f"Asset: {asset.name}", today=date.today())

@bp.route('/admin/assets/<int:asset_id>/delete', methods=['POST'])
@admin_required
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    db.session.delete(asset)
    db.session.commit()
    flash('Asset deleted.', 'success')
    return redirect(url_for('admin.view_assets'))

# --- Vendor Routes ---

@bp.route('/admin/vendors')
@admin_required
def view_vendors():
    vendors = Vendor.query.all()
    return render_template('admin/view_vendors.html', vendors=vendors, title='Manage Vendors', today=date.today())

@bp.route('/admin/vendors/add', methods=['GET', 'POST'])
@admin_required
def add_vendor():
    form = VendorForm()
    if form.validate_on_submit():
        vendor = Vendor(
            name=form.name.data,
            category=form.category.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            services_provided=form.services_provided.data,
            gstin=form.gstin.data,
            bank_account=form.bank_account.data,
            bank_name=form.bank_name.data,
            ifsc_code=form.ifsc_code.data,
            payment_terms=form.payment_terms.data,
            contract_start=form.contract_start.data,
            contract_expiry=form.contract_expiry.data,
            status=form.status.data
        )
        db.session.add(vendor)
        db.session.commit()
        log_audit('CREATE', 'Vendor', vendor.id, f"Added vendor {vendor.name}", current_user)
        flash('Vendor added successfully.', 'success')
        return redirect(url_for('admin.view_vendors'))
    return render_template('admin/add_vendor.html', form=form, title='Add Vendor')

@bp.route('/admin/vendors/<int:vendor_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    form = VendorForm()
    if form.validate_on_submit():
        vendor.name = form.name.data
        vendor.category = form.category.data
        vendor.contact_person = form.contact_person.data
        vendor.email = form.email.data
        vendor.phone = form.phone.data
        vendor.address = form.address.data
        vendor.services_provided = form.services_provided.data
        vendor.gstin = form.gstin.data
        vendor.bank_account = form.bank_account.data
        vendor.bank_name = form.bank_name.data
        vendor.ifsc_code = form.ifsc_code.data
        vendor.payment_terms = form.payment_terms.data
        vendor.contract_start = form.contract_start.data
        vendor.contract_expiry = form.contract_expiry.data
        vendor.status = form.status.data
        db.session.commit()
        log_audit('UPDATE', 'Vendor', vendor.id, f"Updated vendor {vendor.name}", current_user)
        flash('Vendor updated successfully.', 'success')
        return redirect(url_for('admin.view_vendors'))
    elif request.method == 'GET':
        form.name.data = vendor.name
        form.category.data = vendor.category
        form.contact_person.data = vendor.contact_person
        form.email.data = vendor.email
        form.phone.data = vendor.phone
        form.address.data = vendor.address
        form.services_provided.data = vendor.services_provided
        form.gstin.data = vendor.gstin
        form.bank_account.data = vendor.bank_account
        form.bank_name.data = vendor.bank_name
        form.ifsc_code.data = vendor.ifsc_code
        form.payment_terms.data = vendor.payment_terms
        form.contract_start.data = vendor.contract_start
        form.contract_expiry.data = vendor.contract_expiry
        form.status.data = vendor.status
    return render_template('admin/add_vendor.html', form=form, title='Edit Vendor')

@bp.route('/admin/vendors/<int:vendor_id>/view')
@admin_required
def view_vendor_details(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    return render_template('admin/view_vendor_details.html', vendor=vendor, title=f"Vendor: {vendor.name}", today=date.today())

@bp.route('/admin/vendors/<int:vendor_id>/delete', methods=['POST'])
@admin_required
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    db.session.delete(vendor)
    db.session.commit()
    flash('Vendor deleted.', 'success')
    return redirect(url_for('admin.view_vendors'))

@bp.route('/admin/assets/export')
@admin_required
def export_assets():
    assets = Asset.query.all()
    output = export_assets_to_excel(assets)
    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=assets.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

@bp.route('/admin/vendors/export')
@admin_required
def export_vendors():
    vendors = Vendor.query.all()
    output = export_vendors_to_excel(vendors)
    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=vendors.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

@bp.route('/admin/employees/export')
@admin_required
def export_employees():
    query = EmployeeProfile.query.join(User).join(Role).filter(Role.name != 'Admin')
    employees = query.all()
    output = export_employees_to_excel(employees)
    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=employees.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

@bp.route('/admin/employees/template')
@admin_required
def download_employee_template():
    designations = [d.title for d in Designation.query.all()]
    departments = [d.name for d in Department.query.all()]
    output = generate_employee_template(designation_options=designations, department_options=departments)
    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=employee_template.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

@bp.route('/admin/employees/bulk_upload', methods=['POST'])
@admin_required
def bulk_upload_employees():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin.add_employee'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin.add_employee'))
    
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file)
            success_count = 0
            errors = []
            
            emp_role = Role.query.filter_by(name='Employee').first()
            
            for index, row in df.iterrows():
                try:
                    if pd.isna(row['Email']) or pd.isna(row['First Name']):
                        continue
                        
                    if User.query.filter_by(email=row['Email']).first():
                        errors.append(f"Row {index+2}: Email {row['Email']} exists")
                        continue
                        
                    new_id = generate_employee_id()
                    user = User(employeeid=new_id, email=row['Email'], user_role=emp_role, is_first_login=True)
                    user.set_password('pass123')
                    
                    designation = None
                    if not pd.isna(row['Designation']):
                        designation = Designation.query.filter_by(title=row['Designation']).first()
                        
                    department = None
                    if 'Department' in row and not pd.isna(row['Department']):
                        department = Department.query.filter_by(name=row['Department']).first()
                    
                    dob = pd.to_datetime(row['Date of Birth (YYYY-MM-DD)']).date() if not pd.isna(row['Date of Birth (YYYY-MM-DD)']) else None
                    doj = pd.to_datetime(row['Date of Joining (YYYY-MM-DD)']).date() if not pd.isna(row['Date of Joining (YYYY-MM-DD)']) else None
                    
                    profile = EmployeeProfile(
                        first_name=row['First Name'],
                        last_name=row['Last Name'],
                        email=row['Email'],
                        phone_number=str(row['Phone']) if not pd.isna(row['Phone']) else None,
                        date_of_birth=dob,
                        date_of_joining=doj,
                        designation=designation,
                        department=department,
                        gender=row['Gender'] if not pd.isna(row['Gender']) else None,
                        marital_status=row['Marital Status'] if not pd.isna(row['Marital Status']) else None,
                        address=row['Address'] if not pd.isna(row['Address']) else None,
                        pan_number=str(row['PAN']) if not pd.isna(row['PAN']) else None,
                        aadhar_number=str(row['Aadhar']) if not pd.isna(row['Aadhar']) else None,
                        uan_number=str(row['UAN']) if 'UAN' in row and not pd.isna(row['UAN']) else None,
                        pf_number=str(row['PF No']) if 'PF No' in row and not pd.isna(row['PF No']) else None,
                        esi_number=str(row['ESI No']) if 'ESI No' in row and not pd.isna(row['ESI No']) else None,
                        bank_name=row['Bank Name'] if not pd.isna(row['Bank Name']) else None,
                        bank_account_number=str(row['Account Number']) if not pd.isna(row['Account Number']) else None,
                        ifsc_code=row['IFSC'] if not pd.isna(row['IFSC']) else None,
                        branch=row['Branch'] if not pd.isna(row['Branch']) else None,
                        user=user
                    )
                    
                    db.session.add(user)
                    db.session.add(profile)
                    db.session.commit()
                    success_count += 1
                    
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Row {index+2}: {str(e)}")
            
            if success_count > 0:
                flash(f'Successfully uploaded {success_count} employees.', 'success')
            if errors:
                flash(f'Errors: {"; ".join(errors[:3])}...', 'warning')
                
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            
    return redirect(url_for('admin.view_employees'))

@bp.route('/admin/birthdays')
@admin_required
def birthdays():
    today = date.today()
    employees = EmployeeProfile.query.filter(
        extract('month', EmployeeProfile.date_of_birth) == today.month,
        extract('day', EmployeeProfile.date_of_birth) == today.day
    ).all()
    return render_template('admin/birthdays.html', employees=employees, title="Birthdays Today")

@bp.route('/admin/departments')
@admin_required
def departments():
    departments = Department.query.all()
    form = DepartmentForm()
    return render_template('admin/departments.html', departments=departments, form=form, title='Manage Departments')

@bp.route('/admin/departments/add', methods=['POST'])
@admin_required
def add_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        dept = Department(name=form.name.data)
        db.session.add(dept)
        db.session.commit()
        flash('Department added.', 'success')
    return redirect(url_for('admin.departments'))

@bp.route('/admin/departments/<int:dept_id>/delete', methods=['POST'])
@admin_required
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    if dept.employees:
        flash('Cannot delete department with assigned employees.', 'danger')
        return redirect(url_for('admin.departments'))
    db.session.delete(dept)
    db.session.commit()
    flash('Department deleted.', 'success')
    return redirect(url_for('admin.departments'))

# --- ATS Routes ---

@bp.route('/admin/ats/jobs', methods=['GET', 'POST'])
@admin_required
def manage_jobs():
    form = JobOpeningForm()
    if form.validate_on_submit():
        job = JobOpening(
            title=form.title.data,
            department=form.department.data,
            description=form.description.data,
            status=form.status.data
        )
        db.session.add(job)
        db.session.commit()
        log_audit('CREATE', 'JobOpening', job.id, f"Created job '{job.title}'", current_user)
        flash('Job Opening added.', 'success')
        return redirect(url_for('admin.manage_jobs'))
    
    jobs = JobOpening.query.order_by(JobOpening.created_at.desc()).all()
    return render_template('admin/ats_jobs.html', form=form, jobs=jobs, title='Manage Job Openings')

@bp.route('/admin/ats/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_job(job_id):
    job = JobOpening.query.get_or_404(job_id)
    form = JobOpeningForm()
    if form.validate_on_submit():
        job.title = form.title.data
        job.department = form.department.data
        job.description = form.description.data
        job.status = form.status.data
        db.session.commit()
        log_audit('UPDATE', 'JobOpening', job.id, f"Updated job '{job.title}'", current_user)
        flash('Job updated.', 'success')
        return redirect(url_for('admin.manage_jobs'))
    elif request.method == 'GET':
        form.title.data = job.title
        form.department.data = job.department
        form.description.data = job.description
        form.status.data = job.status
    return render_template('admin/edit_ats_job.html', form=form, title='Edit Job')

@bp.route('/admin/ats/candidates', methods=['GET', 'POST'])
@admin_required
def manage_candidates():
    form = CandidateForm()
    if form.validate_on_submit():
        candidate = Candidate(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            job_opening=form.job_opening.data,
            status=form.status.data
        )
        db.session.add(candidate)
        db.session.commit()
        log_audit('CREATE', 'Candidate', candidate.id, f"Added candidate {candidate.first_name} {candidate.last_name}", current_user)
        flash('Candidate added.', 'success')
        return redirect(url_for('admin.manage_candidates'))
    
    candidates = Candidate.query.order_by(Candidate.applied_date.desc()).all()
    return render_template('admin/ats_candidates.html', form=form, candidates=candidates, title='Manage Candidates')

@bp.route('/admin/ats/candidates/<int:cand_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_candidate(cand_id):
    candidate = Candidate.query.get_or_404(cand_id)
    form = CandidateForm()
    if form.validate_on_submit():
        candidate.first_name = form.first_name.data
        candidate.last_name = form.last_name.data
        candidate.email = form.email.data
        candidate.phone = form.phone.data
        candidate.job_opening = form.job_opening.data
        candidate.status = form.status.data
        
        # If hired, prompt to convert to employee? (Advanced: maybe later)
        
        db.session.commit()
        log_audit('UPDATE', 'Candidate', candidate.id, f"Updated candidate {candidate.first_name}", current_user)
        flash('Candidate updated.', 'success')
        return redirect(url_for('admin.manage_candidates'))
    elif request.method == 'GET':
        form.first_name.data = candidate.first_name
        form.last_name.data = candidate.last_name
        form.email.data = candidate.email
        form.phone.data = candidate.phone
        form.job_opening.data = candidate.job_opening
        form.status.data = candidate.status
    return render_template('admin/edit_ats_candidate.html', form=form, title='Edit Candidate')

# --- Task Management Routes ---

@bp.route('/admin/tasks/<int:task_id>/details')
@admin_required
def view_task_details(task_id):
    # Allow if Admin, Director OR has Checklist permission
    if not (current_user.role in ['admin', 'director'] or current_user.has_permission('checklist')):
        flash('You do not have permission to access this ticket.', 'danger')
        return redirect(url_for('admin.dashboard'))

    task = Task.query.get_or_404(task_id)
    roles = Role.query.all()
    return render_template('admin/task_details.html', task=task, roles=roles, title=f"Ticket {task.task_no or task.id}")

@bp.route('/admin/tasks', methods=['GET', 'POST'])
@admin_required
def manage_tasks():
    # Allow if Admin, Director OR has Checklist permission
    if not (current_user.role in ['admin', 'director'] or current_user.has_permission('checklist')):
        flash('You do not have permission to access Checklists.', 'danger')
        return redirect(url_for('admin.dashboard'))

    form = TaskForm()
    if form.validate_on_submit():
        # Auto-numbering logic (T001, T002...)
        last_task = Task.query.order_by(Task.id.desc()).first()
        next_no = "T001"
        if last_task and last_task.task_no:
            try:
                num = int(last_task.task_no[1:]) + 1
                next_no = f"T{num:03d}"
            except:
                pass

        task = Task(
            task_no=next_no,
            description=form.description.data,
            task_type=form.task_type.data,
            other_type_name=form.other_type_name.data,
            status='Assigned',
            priority=form.priority.data,
            assigned_role=form.assigned_role.data,
            task_add_to=form.task_add_to.data,
            target_date=form.target_date.data
        )
        db.session.add(task)
        db.session.flush()

        # Create instance records
        if form.task_add_to.data:
            et = EmployeeTask(employee_id=form.task_add_to.data.id, task_id=task.id)
            db.session.add(et)
        elif form.assigned_role.data:
            role_members = EmployeeProfile.query.join(User).filter(User.role_id == form.assigned_role.data.id, EmployeeProfile.is_resigned == False).all()
            for member in role_members:
                et = EmployeeTask(employee_id=member.id, task_id=task.id)
                db.session.add(et)

        db.session.commit()
        flash(f'Task {next_no} added and assigned successfully.', 'success')
        return redirect(url_for('admin.manage_tasks'))
    
    # Filter & Pagination
    status_filter = request.args.get('status_filter', '')
    page = request.args.get('page', 1, type=int)
    
    query = Task.query.order_by(Task.id.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    tasks = query.paginate(page=page, per_page=10)
    
    return render_template('admin/manage_tasks.html', form=form, tasks=tasks, status_filter=status_filter, title='Manage Task List')

@bp.route('/admin/api/employees_by_role/<int:role_id>')
@admin_required
def get_employees_by_role(role_id):
    employees = EmployeeProfile.query.join(User).filter(
        User.role_id == role_id,
        EmployeeProfile.is_resigned == False
    ).all()
    
    return jsonify([{'id': e.id, 'name': f"{e.first_name} {e.last_name}"} for e in employees])

@bp.route('/admin/tasks/<int:task_id>/edit', methods=['POST'])
@admin_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    new_description = request.form.get('description')
    new_type = request.form.get('task_type')
    new_other = request.form.get('other_type_name')
    new_priority = request.form.get('priority')
    new_status = request.form.get('status') # Get status from form
    new_role_id = request.form.get('assigned_role', type=int)
    new_emp_id = request.form.get('task_add_to', type=int)
    new_target_date_str = request.form.get('target_date')

    # Update basics
    task.description = new_description
    task.task_type = new_type
    task.other_type_name = new_other if new_type == 'Others' else None
    task.priority = new_priority
    
    if new_target_date_str:
        task.target_date = datetime.strptime(new_target_date_str, '%Y-%m-%d').date()
    else:
        task.target_date = None
    
    # Sync status down to instances if changed
    if new_status and new_status != task.status:
        task.status = new_status
        for instance in task.instances:
            instance.status = new_status
            if new_status in ['Completed', 'Rejected']:
                instance.is_completed = (new_status == 'Completed')
                instance.completed_at = datetime.utcnow() if new_status == 'Completed' else None
                instance.completed_by = current_user.email
            else:
                instance.is_completed = False
                instance.completed_at = None

    # Check reassignment
    current_role_id = task.assigned_role_id
    current_emp_id = task.task_add_to_id
    
    # Logic: Reassign if Role changed OR Employee changed
    # Note: If Role is same but Emp changed from None to ID (or vice versa), reassign.
    if new_role_id != current_role_id or new_emp_id != current_emp_id:
        # Delete old instances
        EmployeeTask.query.filter_by(task_id=task.id).delete()
        
        # Update Master Task Assignment
        task.assigned_role_id = new_role_id
        task.task_add_to_id = new_emp_id
        task.status = 'Assigned' # Reset status on reassignment

        # Create new instances
        if new_emp_id:
            et = EmployeeTask(employee_id=new_emp_id, task_id=task.id)
            db.session.add(et)
        elif new_role_id:
            role_members = EmployeeProfile.query.join(User).filter(User.role_id == new_role_id, EmployeeProfile.is_resigned == False).all()
            for member in role_members:
                et = EmployeeTask(employee_id=member.id, task_id=task.id)
                db.session.add(et)
        
        flash('Task updated and reassigned.', 'success')
    else:
        flash('Task details updated.', 'success')

    db.session.commit()
    return redirect(url_for('admin.view_task_details', task_id=task.id))

@bp.route('/admin/tasks/<int:task_id>/delete', methods=['POST'])
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('admin.manage_tasks'))

@bp.route('/admin/employee_task/<int:emp_task_id>/toggle', methods=['POST'])
@admin_required
def toggle_employee_task(emp_task_id):
    task = EmployeeTask.query.get_or_404(emp_task_id)
    task.is_completed = not task.is_completed
    if task.is_completed:
        task.completed_at = datetime.utcnow()
        task.completed_by = current_user.email
    else:
        task.completed_at = None
        task.completed_by = None
    db.session.commit()
    return redirect(url_for('admin.admin_view_employee_profile', employee_id=task.employee_id))

# --- Performance Management Routes ---

@bp.route('/admin/employee/<int:employee_id>/upload_document', methods=['POST'])
@admin_required
def upload_employee_document(employee_id):
    employee = EmployeeProfile.query.get_or_404(employee_id)
    form = EmployeeDocumentForm()
    if form.validate_on_submit():
        if form.file.data:
            filename = save_file(form.file.data, folder='documents')
            
            doc = EmployeeDocument(
                title=form.title.data,
                document_type=form.document_type.data,
                file_path=filename,
                employee_id=employee.id
            )
            db.session.add(doc)
            db.session.commit()
            log_audit('CREATE', 'EmployeeDocument', doc.id, f"Uploaded document '{doc.title}' for {employee.first_name}", current_user)
            flash('Document uploaded successfully.', 'success')
    return redirect(url_for('admin.admin_view_employee_profile', employee_id=employee.id))

@bp.route('/admin/document/<int:doc_id>/delete', methods=['POST'])
@admin_required
def delete_employee_document(doc_id):
    doc = EmployeeDocument.query.get_or_404(doc_id)
    emp_id = doc.employee_id
    from flask import current_app
    file_path = os.path.join(current_app.root_path, 'static/documents', doc.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(doc)
    db.session.commit()
    flash('Document deleted.', 'success')
    return redirect(url_for('admin.admin_view_employee_profile', employee_id=emp_id))

@bp.route('/admin/announcements', methods=['GET', 'POST'])
@admin_required
def manage_announcements():
    from employee_portal.models import Announcement
    form = AnnouncementForm()
    if form.validate_on_submit():
        ann = Announcement(
            title=form.title.data,
            content=form.content.data,
            is_active=form.is_active.data,
            posted_by=current_user.email
        )
        db.session.add(ann)
        db.session.commit()
        log_audit('CREATE', 'Announcement', ann.id, f"Posted announcement '{ann.title}'", current_user)
        flash('Announcement posted.', 'success')
        return redirect(url_for('admin.manage_announcements'))
    
    announcements = Announcement.query.order_by(Announcement.date_posted.desc()).all()
    return render_template('admin/manage_announcements.html', form=form, announcements=announcements, title='Manage Announcements')

@bp.route('/admin/announcements/<int:ann_id>/toggle', methods=['POST'])
@admin_required
def toggle_announcement(ann_id):
    from employee_portal.models import Announcement
    ann = Announcement.query.get_or_404(ann_id)
    ann.is_active = not ann.is_active
    db.session.commit()
    return redirect(url_for('admin.manage_announcements'))

@bp.route('/admin/announcements/<int:ann_id>/delete', methods=['POST'])
@admin_required
def delete_announcement(ann_id):
    from employee_portal.models import Announcement
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    log_audit('DELETE', 'Announcement', ann_id, f"Deleted announcement '{ann.title}'", current_user)
    flash('Announcement deleted.', 'success')
    return redirect(url_for('admin.manage_announcements'))

@bp.route('/admin/holidays', methods=['GET', 'POST'])
@admin_required
def manage_holidays():
    form = HolidayForm()
    if form.validate_on_submit():
        holiday = Holiday(
            name=form.name.data,
            date=form.date.data,
            description=form.description.data
        )
        db.session.add(holiday)
        try:
            db.session.commit()
            log_audit('CREATE', 'Holiday', holiday.id, f"Added holiday '{holiday.name}' on {holiday.date}", current_user)
            flash('Holiday added successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding holiday: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_holidays'))
    
    today = date.today()
    selected_year = request.args.get('year', type=int)
    
    if selected_year:
        # Show all holidays for the selected year
        holidays = Holiday.query.filter(extract('year', Holiday.date) == selected_year).order_by(Holiday.date.asc()).all()
    else:
        # Default: Show today and future holidays
        holidays = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date.asc()).all()
    
    # Get all distinct years from DB for the dropdown
    all_years_query = db.session.query(extract('year', Holiday.date)).distinct().all()
    all_years = sorted([int(y[0]) for y in all_years_query if y[0]], reverse=True)
    if not all_years: all_years = [today.year]

    return render_template('admin/manage_holidays.html', form=form, holidays=holidays, today=today, all_years=all_years, selected_year=selected_year, title='Manage Holidays')

@bp.route('/admin/holidays/view')
@admin_required
def view_holidays():
    selected_year = request.args.get('year', date.today().year, type=int)
    holidays = Holiday.query.filter(extract('year', Holiday.date) == selected_year).order_by(Holiday.date.asc()).all()
    
    # Get available years for the dropdown
    available_years = db.session.query(extract('year', Holiday.date)).distinct().order_by(extract('year', Holiday.date).desc()).all()
    years = [int(y[0]) for y in available_years] if available_years else [date.today().year]
    
    return render_template('admin/view_holidays.html', holidays=holidays, selected_year=selected_year, years=years, title='Holiday Calendar')

@bp.route('/admin/holidays/<int:holiday_id>/delete', methods=['POST'])
@admin_required
def delete_holiday(holiday_id):
    from employee_portal.models import Holiday
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    flash('Holiday deleted.', 'success')
    return redirect(url_for('admin.manage_holidays'))

@bp.route('/admin/holidays/template')
@admin_required
def download_holiday_template_route():
    output = generate_holiday_template()
    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=holiday_template.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

@bp.route('/admin/holidays/bulk_upload', methods=['POST'])
@admin_required
def bulk_upload_holidays():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin.manage_holidays'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin.manage_holidays'))
    
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            from employee_portal.models import Holiday
            df = pd.read_excel(file)
            success_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    if pd.isna(row['Holiday Name']) or pd.isna(row['Date (YYYY-MM-DD)']):
                        continue
                    
                    holiday_date = pd.to_datetime(row['Date (YYYY-MM-DD)']).date()
                    
                    # Check if already exists
                    existing = Holiday.query.filter_by(date=holiday_date).first()
                    if existing:
                        errors.append(f"Row {index+2}: Holiday on {holiday_date} already exists")
                        continue
                    
                    holiday = Holiday(
                        name=row['Holiday Name'],
                        date=holiday_date,
                        description=row['Description'] if not pd.isna(row['Description']) else None
                    )
                    db.session.add(holiday)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index+2}: {str(e)}")
            
            db.session.commit()
            
            if success_count > 0:
                flash(f'Successfully uploaded {success_count} holidays.', 'success')
                log_audit('BULK_CREATE', 'Holiday', None, f"Bulk uploaded {success_count} holidays", current_user)
            if errors:
                flash(f'Errors encountered: {", ".join(errors[:3])}...', 'warning')
                
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            
    return redirect(url_for('admin.manage_holidays'))

@bp.route('/admin/expenses')
@admin_required
def manage_expenses():
    claims = ExpenseClaim.query.order_by(ExpenseClaim.status == 'Pending', ExpenseClaim.applied_date.desc()).all()
    return render_template('admin/manage_expenses.html', claims=claims, title='Manage Expense Claims')

@bp.route('/admin/expense_action/<int:claim_id>/<string:action>', methods=['POST'])
@admin_required
def expense_action(claim_id, action):
    claim = ExpenseClaim.query.get_or_404(claim_id)
    if action == 'approve':
        claim.status = 'Approved'
        claim.approved_by = current_user.email
        flash('Expense claim approved.', 'success')
    elif action == 'reject':
        claim.status = 'Rejected'
        claim.approved_by = current_user.email
        claim.rejection_reason = request.form.get('reason', '')
        flash('Expense claim rejected.', 'warning')
    elif action == 'pay':
        claim.status = 'Paid'
        
        # Create Debit Record
        debit = Debit(
            date=date.today(),
            amount=claim.amount,
            description=f"Expense Claim: {claim.title} - {claim.employee.first_name} {claim.employee.last_name}",
            category='Expense Claim',
            payment_mode='Bank Transfer',
            reference_number=f"EXP-{claim.id}"
        )
        db.session.add(debit)
        
        flash('Expense claim marked as Paid and Debit recorded.', 'success')
    
    db.session.commit()
    log_audit('UPDATE', 'ExpenseClaim', claim.id, f"Action {action} on claim '{claim.title}'", current_user)
    return redirect(url_for('admin.manage_expenses'))

@bp.route('/admin/appraisals', methods=['GET', 'POST'])
@admin_required
def manage_appraisals():
    form = AppraisalForm()
    if form.validate_on_submit():
        appraisal = Appraisal(
            employee=form.employee.data,
            reviewer=current_user.profile,
            period=form.period.data,
            score=form.score.data,
            feedback=form.feedback.data,
            goals=form.goals.data,
            status=form.status.data
        )
        db.session.add(appraisal)
        db.session.commit()
        log_audit('CREATE', 'Appraisal', appraisal.id, f"Created appraisal for {appraisal.employee.first_name} ({appraisal.period})", current_user)
        flash('Appraisal recorded.', 'success')
        return redirect(url_for('admin.manage_appraisals'))
    
    appraisals = Appraisal.query.order_by(Appraisal.appraisal_date.desc()).all()
    return render_template('admin/manage_appraisals.html', form=form, appraisals=appraisals, title='Manage Appraisals')

@bp.route('/admin/appraisals/<int:appraisal_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_appraisal(appraisal_id):
    appraisal = Appraisal.query.get_or_404(appraisal_id)
    form = AppraisalForm()
    if form.validate_on_submit():
        appraisal.employee = form.employee.data
        appraisal.period = form.period.data
        appraisal.score = form.score.data
        appraisal.feedback = form.feedback.data
        appraisal.goals = form.goals.data
        appraisal.status = form.status.data
        db.session.commit()
        log_audit('UPDATE', 'Appraisal', appraisal.id, f"Updated appraisal for {appraisal.employee.first_name}", current_user)
        flash('Appraisal updated.', 'success')
        return redirect(url_for('admin.manage_appraisals'))
    elif request.method == 'GET':
        form.employee.data = appraisal.employee
        form.period.data = appraisal.period
        form.score.data = appraisal.score
        form.feedback.data = appraisal.feedback
        form.goals.data = appraisal.goals
        form.status.data = appraisal.status
    return render_template('admin/edit_appraisal.html', form=form, title='Edit Appraisal')

# --- Liquidity Management ---

@bp.route('/admin/liquidity/credits')
@admin_required
def manage_credits():
    credits = Credit.query.order_by(Credit.date.desc()).all()
    return render_template('admin/manage_credits.html', title='Manage Credits', credits=credits)

@bp.route('/admin/liquidity/credits/add', methods=['GET', 'POST'])
@admin_required
def add_credit():
    form = CreditForm()
    if form.validate_on_submit():
        credit = Credit(
            date=form.date.data,
            amount=form.amount.data,
            description=form.description.data,
            category=form.category.data,
            payment_mode=form.payment_mode.data,
            reference_number=form.reference_number.data
        )
        db.session.add(credit)
        db.session.commit()
        log_audit('CREATE', 'Credit', credit.id, f'Added credit of {form.amount.data} ({form.category.data})', current_user)
        flash('Credit transaction added successfully!', 'success')
        return redirect(url_for('admin.manage_credits'))
    return render_template('admin/add_credit.html', title='Add Credit', form=form)

@bp.route('/admin/bill_estimation', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def bill_estimation():
    form = BillEstimationForm()
    if request.method == 'POST':
        try:
            items = json.loads(request.form.get('items_json', '[]'))
            date_str = request.form.get('date')
            total_amount = float(request.form.get('total_amount') or 0)
            
            # Generate Estimate Number
            
            # Generate Estimate Number
            est_num = f"EST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Save to DB
            estimate = BillEstimate(
                estimate_number=est_num,
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                total_amount=total_amount,
                items_json=json.dumps(items),
                created_by=current_user.email
            )
            db.session.add(estimate)
            db.session.commit()
            
            data = {
                'date': date_str,
                'items': items,
                'total_amount': total_amount,
                'estimate_number': est_num
            }
            
            filename = generate_bill_estimate_pdf(data)
            
            # Update record with filename
            estimate.pdf_file = filename
            db.session.commit()
            
            return send_from_directory(directory='../instance', path=filename, as_attachment=True)
            
        except Exception as e:
            flash(f'Error generating estimate: {e}', 'danger')
            return redirect(url_for('admin.bill_estimation'))
            
    return render_template('admin/bill_estimation.html', title='Bill Estimation', form=form)

@bp.route('/admin/bill_estimation/history')
@admin_required
def bill_estimation_history():
    estimates = BillEstimate.query.order_by(BillEstimate.created_at.desc()).all()
    return render_template('admin/bill_estimation_history.html', title='Estimation History', estimates=estimates)

@bp.route('/admin/bill_estimation/download/<int:estimate_id>')
@admin_required
def download_estimate(estimate_id):
    estimate = BillEstimate.query.get_or_404(estimate_id)
    if not estimate.pdf_file:
        flash('PDF file not found for this estimate.', 'danger')
        return redirect(url_for('admin.bill_estimation_history'))
    return send_from_directory(directory='../instance', path=estimate.pdf_file, as_attachment=False)

@bp.route('/admin/bill_estimation/delete/<int:estimate_id>', methods=['POST'])
@admin_required
def delete_estimate(estimate_id):
    estimate = BillEstimate.query.get_or_404(estimate_id)
    
    # Optional: Delete the file from disk
    if estimate.pdf_file:
        try:
            file_path = os.path.join(current_app.instance_path, estimate.pdf_file)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    db.session.delete(estimate)
    db.session.commit()
    log_audit('DELETE', 'BillEstimate', estimate.id, f'Deleted estimate {estimate.estimate_number}', current_user)
    flash('Estimate deleted successfully.', 'success')
    return redirect(url_for('admin.bill_estimation_history'))

@bp.route('/admin/bill_estimation/edit/<int:estimate_id>', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def edit_estimate(estimate_id):
    estimate = BillEstimate.query.get_or_404(estimate_id)
    form = BillEstimationForm(obj=estimate)
    
    if request.method == 'POST':
        try:
            items = json.loads(request.form.get('items_json', '[]'))
            date_str = request.form.get('date')
            total_amount = float(request.form.get('total_amount') or 0)
            
            # Generate Estimate Number
            
            # Update DB record
            estimate.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            estimate.total_amount = total_amount
            estimate.items_json = json.dumps(items)
            
            # Regenerate PDF
            data = {
                'date': date_str,
                'items': items,
                'total_amount': total_amount,
                'estimate_number': estimate.estimate_number
            }
            
            # Remove old file if needed, or just overwrite. 
            # Generating new filename to avoid cache issues or conflicts if date changed.
            # But standard practice might be to keep same name or generate new one.
            # Let's generate new one to be safe.
            old_file = estimate.pdf_file
            
            filename = generate_bill_estimate_pdf(data)
            estimate.pdf_file = filename
            
            db.session.commit()
            
            # Cleanup old file
            if old_file and old_file != filename:
                try:
                    old_path = os.path.join(current_app.instance_path, old_file)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    print(f"Error removing old PDF: {e}")

            flash('Estimate updated successfully.', 'success')
            return redirect(url_for('admin.bill_estimation_history'))
            
        except Exception as e:
            flash(f'Error updating estimate: {e}', 'danger')
            return redirect(url_for('admin.edit_estimate', estimate_id=estimate.id))
    
    return render_template('admin/bill_estimation.html', title='Edit Estimate', form=form)

@bp.route('/admin/liquidity/debits')
@admin_required
def manage_debits():
    query = Debit.query
    
    # Filters
    paid_by = request.args.get('paid_by')
    amount = request.args.get('amount')
    category = request.args.get('category')
    
    if paid_by:
        query = query.filter(Debit.paid_by.ilike(f'%{paid_by}%'))
    if amount:
        try:
            amt = float(amount)
            query = query.filter(Debit.amount == amt)
        except ValueError:
            pass # Ignore invalid amount
    if category:
        query = query.filter(Debit.category == category)
        
    debits = query.order_by(Debit.date.desc()).all()
    return render_template('admin/manage_debits.html', title='Manage Debits', debits=debits)

@bp.route('/admin/liquidity/debits/add', methods=['GET', 'POST'])
@admin_required
def add_debit():
    form = DebitForm()
    
    # Populate 'Paid By' with Directors
    directors = User.query.join(Role).filter(Role.name == 'Director').all()
    director_choices = [(d.profile.first_name + ' ' + d.profile.last_name, d.profile.first_name + ' ' + d.profile.last_name) for d in directors if d.profile]
    # Fallback or additional option
    director_choices.insert(0, ('Company', 'Company Account'))
    form.paid_by.choices = director_choices

    if form.validate_on_submit():
        bill_filename = None
        if form.bill.data:
            bill_filename = save_file(form.bill.data, 'documents')

        debit = Debit(
            date=form.date.data,
            amount=form.amount.data,
            description=form.description.data,
            category=form.category.data,
            payment_mode=form.payment_mode.data,
            reference_number=form.reference_number.data,
            bill_file=bill_filename,
            paid_by=form.paid_by.data
        )
        db.session.add(debit)
        db.session.commit()
        log_audit('CREATE', 'Debit', debit.id, f'Added debit of {form.amount.data} ({form.category.data})', current_user)
        flash('Debit transaction added successfully!', 'success')
        return redirect(url_for('admin.manage_debits'))
    return render_template('admin/add_debit.html', title='Add Debit', form=form)

@bp.route('/admin/liquidity/debits/<int:debit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_debit(debit_id):
    debit = Debit.query.get_or_404(debit_id)
    form = DebitForm(obj=debit)
    
    # Populate 'Paid By'
    directors = User.query.join(Role).filter(Role.name == 'Director').all()
    director_choices = [(d.profile.first_name + ' ' + d.profile.last_name, d.profile.first_name + ' ' + d.profile.last_name) for d in directors if d.profile]
    director_choices.insert(0, ('Company', 'Company Account'))
    form.paid_by.choices = director_choices
    
    if request.method == 'GET':
        form.paid_by.data = debit.paid_by

    if form.validate_on_submit():
        if form.bill.data:
            bill_filename = save_file(form.bill.data, 'documents')
            debit.bill_file = bill_filename
            
        debit.date = form.date.data
        debit.amount = form.amount.data
        debit.description = form.description.data
        debit.category = form.category.data
        debit.payment_mode = form.payment_mode.data
        debit.reference_number = form.reference_number.data
        debit.paid_by = form.paid_by.data
        
        db.session.commit()
        log_audit('UPDATE', 'Debit', debit.id, f'Updated debit of {form.amount.data}', current_user)
        flash('Debit transaction updated successfully!', 'success')
        return redirect(url_for('admin.manage_debits'))
        
    return render_template('admin/edit_debit.html', title='Edit Debit', form=form)

@bp.route('/admin/liquidity/debits/<int:debit_id>/delete', methods=['POST'])
@admin_required
def delete_debit(debit_id):
    debit = Debit.query.get_or_404(debit_id)
    db.session.delete(debit)
    db.session.commit()
    log_audit('DELETE', 'Debit', debit.id, f'Deleted debit transaction of {debit.amount}', current_user)
    flash('Debit transaction deleted successfully!', 'success')
    return redirect(url_for('admin.manage_debits'))

@bp.route('/admin/liquidity/debits/export_pdf', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def export_debits_pdf():
    month_str = request.args.get('month') or request.form.get('month')
    if not month_str:
        flash('Please select a month to export.', 'warning')
        return redirect(url_for('admin.manage_debits'))

    try:
        year, month = map(int, month_str.split('-'))
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        debits = Debit.query.filter(Debit.date >= start_date, Debit.date < end_date).order_by(Debit.date.asc()).all()

        if not debits:
            flash('No debit records found for the selected month.', 'info')
            return redirect(url_for('admin.manage_debits'))

        total_amount = sum(d.amount for d in debits)
        filename = generate_transactions_pdf(debits, f"Debit Transactions - {start_date.strftime('%B %Y')}", total_amount)
        
        return send_from_directory(directory='../instance', path=filename, as_attachment=True)

    except ValueError:
        flash('Invalid month format.', 'danger')
        return redirect(url_for('admin.manage_debits'))

@bp.route('/admin/liquidity/credits/export_pdf', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def export_credits_pdf():
    month_str = request.args.get('month') or request.form.get('month')
    if not month_str:
        flash('Please select a month to export.', 'warning')
        return redirect(url_for('admin.manage_credits'))

    try:
        year, month = map(int, month_str.split('-'))
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        credits = Credit.query.filter(Credit.date >= start_date, Credit.date < end_date).order_by(Credit.date.asc()).all()

        if not credits:
            flash('No credit records found for the selected month.', 'info')
            return redirect(url_for('admin.manage_credits'))

        total_amount = sum(c.amount for c in credits)
        filename = generate_transactions_pdf(credits, f"Credit Transactions - {start_date.strftime('%B %Y')}", total_amount)
        
        return send_from_directory(directory='../instance', path=filename, as_attachment=True)

    except ValueError:
        flash('Invalid month format.', 'danger')
        return redirect(url_for('admin.manage_credits'))

@bp.route('/admin/liquidity/invoices')
@admin_required
def manage_invoices():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    return render_template('admin/manage_invoices.html', title='Manage Invoices', invoices=invoices)

@bp.route('/admin/liquidity/invoices/add', methods=['GET', 'POST'])
@admin_required
def add_invoice():
    form = InvoiceForm()
    if form.validate_on_submit():
        file_filename = None
        if form.file.data:
            file_filename = save_file(form.file.data, 'documents')
            
        invoice = Invoice(
            invoice_number=form.invoice_number.data,
            date=form.date.data,
            due_date=form.due_date.data,
            vendor=form.vendor.data,
            amount=form.amount.data,
            status=form.status.data,
            description=form.description.data,
            file_path=file_filename
        )
        db.session.add(invoice)
        db.session.commit()
        log_audit('CREATE', 'Invoice', invoice.id, f'Added invoice {form.invoice_number.data} for {form.vendor.data.name}', current_user)
        flash('Invoice added successfully!', 'success')
        return redirect(url_for('admin.manage_invoices'))
    return render_template('admin/add_invoice.html', title='Add Invoice', form=form)

@bp.route('/admin/liquidity/invoices/<int:invoice_id>/pay', methods=['POST'])
@admin_required
def pay_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.status == 'Paid':
        flash('Invoice is already paid.', 'warning')
        return redirect(url_for('admin.manage_invoices'))
        
    invoice.status = 'Paid'
    
    # Create Debit Record
    debit = Debit(
        date=date.today(),
        amount=invoice.amount,
        description=f"Invoice Payment: {invoice.invoice_number} - {invoice.vendor.name if invoice.vendor else 'Unknown'}",
        category='Vendor Payment',
        payment_mode='Bank Transfer',
        reference_number=f"INV-{invoice.id}"
    )
    db.session.add(debit)
    db.session.commit()
    
    log_audit('UPDATE', 'Invoice', invoice.id, f'Marked invoice {invoice.invoice_number} as Paid', current_user)
    flash('Invoice marked as Paid and Debit record created.', 'success')
    return redirect(url_for('admin.manage_invoices'))

@bp.route('/admin/liquidity/cash-position')
@admin_required
def cash_position():
    total_credits = db.session.query(db.func.sum(Credit.amount)).scalar() or 0
    total_debits = db.session.query(db.func.sum(Debit.amount)).scalar() or 0
    closing_balance = total_credits - total_debits
    
    return render_template('admin/cash_position.html', 
                           title='Cash Position', 
                           total_credits=total_credits, 
                           total_debits=total_debits, 
                           closing_balance=closing_balance)

@bp.route('/admin/liquidity/purchase-orders')
@admin_required
def manage_purchase_orders():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.date.desc()).all()
    return render_template('admin/manage_purchase_orders.html', title='Manage Purchase Orders', orders=orders)

@bp.route('/admin/liquidity/signatures')
@admin_required
def manage_signatures():
    # List all authorized signatures
    signatures = AuthorizedSignature.query.all()
    return render_template('admin/manage_signatures.html', title='Manage Signatures', signatures=signatures)

@bp.route('/admin/liquidity/signatures/add', methods=['GET', 'POST'])
@admin_required
def add_signature():
    form = AuthorizedSignatureForm()
    if form.validate_on_submit():
        file_filename = save_file(form.file.data, 'img')
        sig = AuthorizedSignature(
            name=form.name.data,
            designation=form.designation.data,
            file_path=file_filename
        )
        db.session.add(sig)
        db.session.commit()
        log_audit('CREATE', 'AuthorizedSignature', sig.id, f"Added signature for {sig.name}", current_user)
        flash('Signature added successfully!', 'success')
        return redirect(url_for('admin.manage_signatures'))
    return render_template('admin/add_signature.html', title='Add Signature', form=form)

@bp.route('/admin/liquidity/purchase-orders/add', methods=['GET', 'POST'])
@admin_required
def add_purchase_order():
    form = PurchaseOrderForm()
    if form.validate_on_submit():
        # Directly get JSON from request to avoid any WTForms processing issues
        raw_items_json = request.form.get('items_json', '[]')
        
        po = PurchaseOrder(
            po_number=form.po_number.data,
            date=form.date.data,
            vendor=form.vendor.data,
            items_json=raw_items_json,
            tax_percentage=form.tax_percentage.data,
            total_amount=form.total_amount.data,
            status=form.status.data,
            signature=form.authorized_signature.data,
            notes=form.notes.data
        )
        db.session.add(po)
        db.session.commit()
        log_audit('CREATE', 'PurchaseOrder', po.id, f'Added Purchase Order {form.po_number.data} for {form.vendor.data.name}', current_user)
        flash('Purchase Order created successfully!', 'success')
        return redirect(url_for('admin.manage_purchase_orders'))
    
    # Pre-fill PO Number if GET request
    if request.method == 'GET':
        random_num = random.randint(1000, 9999)
        date_str = date.today().strftime('%d%m%y')
        form.po_number.data = f"PO{random_num}{date_str}"
        
    return render_template('admin/add_purchase_order.html', title='Create Purchase Order', form=form)

@bp.route('/admin/liquidity/purchase-orders/<int:po_id>/print')
@admin_required
def print_purchase_order(po_id):
    po = PurchaseOrder.query.get_or_404(po_id)
    
    # Parse items JSON if it's a string
    items = []
    if po.items_json:
        try:
            parsed = json.loads(po.items_json)
            if isinstance(parsed, list):
                items = parsed
            else:
                items = [{'item': po.items_json, 'qty': '-', 'price': '-'}]
        except:
            # If not valid JSON, treat as a single description item or plain text
            items = [{'item': po.items_json, 'qty': '-', 'price': '-'}]
            
    return render_template('admin/print_purchase_order.html', po=po, items=items, today=date.today())

@bp.route('/admin/liquidity/purchase-orders/<int:po_id>/delete', methods=['POST'])
@admin_required
def delete_purchase_order(po_id):
    po = PurchaseOrder.query.get_or_404(po_id)
    db.session.delete(po)
    db.session.commit()
    log_audit('DELETE', 'PurchaseOrder', po.id, f"Deleted PO {po.po_number}", current_user)
    flash('Purchase Order deleted successfully.', 'success')
    return redirect(url_for('admin.manage_purchase_orders'))

@bp.route('/admin/shifts', methods=['GET', 'POST'])
def manage_shifts():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    is_admin = current_user.role in ['admin', 'director']
    can_edit = is_admin or current_user.has_permission('edit_shifts')
    can_view = is_admin or current_user.has_permission('view_shifts')
    is_manager = current_user.profile and current_user.profile.subordinates
    
    if not (can_view or is_manager):
        flash('You do not have permission to access the Shift Plan.')
        return redirect(url_for('main.index'))

    # Helper to get filtered employees
    def get_filtered_employees():
        if is_admin:
            return EmployeeProfile.query.filter_by(is_resigned=False).order_by(EmployeeProfile.first_name).all()
        elif is_manager:
            return EmployeeProfile.query.filter_by(manager_id=current_user.profile.id, is_resigned=False).order_by(EmployeeProfile.first_name).all()
        else:
            return [current_user.profile]

    form = ShiftForm()
    form.employee.query = get_filtered_employees()
    
    selected_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()
    
    if form.validate_on_submit():
        if not (can_edit or is_manager):
            flash('You do not have permission to assign shifts.', 'danger')
            return redirect(url_for('admin.manage_shifts', date=selected_date_str))
            
        start_date = form.date.data
        end_date = form.end_date.data if form.end_date.data else start_date
        
        if end_date < start_date:
            flash('End date cannot be before start date.', 'danger')
            return redirect(url_for('admin.manage_shifts', date=start_date.strftime('%Y-%m-%d')))
            
        current_d = start_date
        count = 0
        while current_d <= end_date:
            existing = ShiftSchedule.query.filter_by(employee_id=form.employee.data.id, date=current_d).first()
            if existing:
                existing.shift_type = form.shift_type.data
                existing.assigned_by = current_user.email
            else:
                shift = ShiftSchedule(
                    employee=form.employee.data,
                    date=current_d,
                    shift_type=form.shift_type.data,
                    assigned_by=current_user.email
                )
                db.session.add(shift)
            current_d += timedelta(days=1)
            count += 1
        
        db.session.commit()
        log_audit('ASSIGN_SHIFT', 'ShiftSchedule', form.employee.data.id, f"Assigned {form.shift_type.data} to {form.employee.data.first_name} from {start_date} to {end_date}", current_user)
        flash(f'Shift assigned for {count} day(s).', 'success')
        return redirect(url_for('admin.manage_shifts', date=start_date.strftime('%Y-%m-%d')))

    # Get shifts for the selected date
    base_query = ShiftSchedule.query.filter_by(date=target_date)
    if not is_admin:
        if is_manager:
            base_query = base_query.join(EmployeeProfile).filter(EmployeeProfile.manager_id == current_user.profile.id)
        else:
            base_query = base_query.join(EmployeeProfile).filter(EmployeeProfile.department_id == current_user.profile.department_id)

    general_shifts = base_query.filter(ShiftSchedule.shift_type == 'General').all()
    morning_shifts = base_query.filter(ShiftSchedule.shift_type == 'Morning').all()
    noon_shifts = base_query.filter(ShiftSchedule.shift_type == 'Noon').all()
    night_shifts = base_query.filter(ShiftSchedule.shift_type == 'Night').all()
    
    return render_template('admin/manage_shifts.html', 
                           title='Shift Plan', 
                           form=form, 
                           general_shifts=general_shifts,
                           morning_shifts=morning_shifts,
                           noon_shifts=noon_shifts,
                           night_shifts=night_shifts,
                           selected_date=target_date.strftime('%Y-%m-%d'))

@bp.route('/admin/liquidity/purchase-orders/<int:po_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_purchase_order(po_id):
    po = PurchaseOrder.query.get_or_404(po_id)
    form = PurchaseOrderForm()
    
    if form.validate_on_submit():
        raw_items_json = request.form.get('items_json', '[]')
        old_status = po.status
        
        po.po_number = form.po_number.data
        po.date = form.date.data
        po.vendor = form.vendor.data
        po.items_json = raw_items_json
        po.total_amount = form.total_amount.data
        po.tax_percentage = form.tax_percentage.data
        po.status = form.status.data
        po.signature = form.authorized_signature.data
        po.notes = form.notes.data
        
        # If moving to Paid, create a Debit record
        if po.status == 'Paid' and old_status != 'Paid':
            debit = Debit(
                date=date.today(),
                amount=po.total_amount,
                description=f"Purchase Order Paid: {po.po_number} - {po.vendor.name}",
                category='Procurement',
                payment_mode='Bank Transfer',
                reference_number=po.po_number
            )
            db.session.add(debit)
            flash('Purchase Order updated and marked as Paid. Debit record created.', 'success')
        else:
            flash('Purchase Order updated successfully.', 'success')
            
        db.session.commit()
        log_audit('UPDATE', 'PurchaseOrder', po.id, f"Updated PO {po.po_number}", current_user)
        flash('Purchase Order updated successfully.', 'success')
        return redirect(url_for('admin.manage_purchase_orders'))
        
    elif request.method == 'GET':
        form.po_number.data = po.po_number
        form.date.data = po.date
        form.vendor.data = po.vendor
        form.items_json.data = po.items_json
        form.total_amount.data = po.total_amount
        form.tax_percentage.data = po.tax_percentage
        form.status.data = po.status
        form.authorized_signature.data = po.signature
        form.notes.data = po.notes
        
    return render_template('admin/add_purchase_order.html', title='Edit Purchase Order', form=form, po=po)

@bp.route('/admin/liquidity/purchase-orders/<int:po_id>/status/<string:status>', methods=['POST'])
@admin_required
def update_po_status(po_id, status):
    po = PurchaseOrder.query.get_or_404(po_id)
    old_status = po.status
    po.status = status
    
    # If moving to Paid, create a Debit record
    if status == 'Paid' and old_status != 'Paid':
        debit = Debit(
            date=date.today(),
            amount=po.total_amount,
            description=f"Purchase Order Paid: {po.po_number} - {po.vendor.name}",
            category='Procurement',
            payment_mode='Bank Transfer', # Default
            reference_number=po.po_number
        )
        db.session.add(debit)
        flash(f'PO marked as Paid and Debit record created.', 'success')
    else:
        flash(f'PO status updated to {status}.', 'success')
        
    db.session.commit()
    log_audit('UPDATE', 'PurchaseOrder', po.id, f"Updated status to {status}", current_user)
    return redirect(url_for('admin.manage_purchase_orders'))

@bp.route('/admin/shifts/calendar')
def view_shifts_calendar():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    is_admin = current_user.role in ['admin', 'director']
    is_manager = current_user.profile and current_user.profile.subordinates
    can_view = is_admin or current_user.has_permission('view_shifts')
    
    if not (can_view or is_manager):
        flash('Permission denied.')
        return redirect(url_for('main.index'))

    # Get month/year from args or default to current
    try:
        year = int(request.args.get('year', date.today().year))
        month = int(request.args.get('month', date.today().month))
    except ValueError:
        year = date.today().year
        month = date.today().month

    # Calculate date range for the month
    import calendar
    num_days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)

    # Fetch shifts
    query = ShiftSchedule.query.filter(ShiftSchedule.date >= start_date, ShiftSchedule.date <= end_date)
    
    if not is_admin:
        # If manager, show team. If employee with view_shifts, show all team members? 
        # Usually employees should see teammates. Let's show shifts for the same manager if they are an employee.
        if is_manager:
            query = query.join(EmployeeProfile).filter(EmployeeProfile.manager_id == current_user.profile.id)
        elif can_view:
            # If they have view permission, they can see shifts for their department
            if current_user.profile and current_user.profile.department_id:
                query = query.join(EmployeeProfile).filter(EmployeeProfile.department_id == current_user.profile.department_id)
            else:
                # Fallback to just self if no department
                query = query.filter(ShiftSchedule.employee_id == current_user.profile.id)
        
    shifts = query.all()
    
    # Fetch holidays for the month
    month_holidays = Holiday.query.filter(
        extract('year', Holiday.date) == year,
        extract('month', Holiday.date) == month
    ).all()
    holidays_dict = {h.date.day: h.name for h in month_holidays}
    
    # Organize by day: {1: [shift, shift], 2: [], ...}
    calendar_data = {d: [] for d in range(1, num_days + 1)}
    for shift in shifts:
        day = shift.date.day
        calendar_data[day].append(shift)

    month_name = calendar.month_name[month]
    
    return render_template('admin/view_shifts_calendar.html', 
                           calendar_data=calendar_data, 
                           holidays=holidays_dict,
                           year=year, 
                           month=month, 
                           month_name=month_name, 
                           today=date.today(),
                           date=date)

@bp.route('/admin/shifts/team-plan')
def view_team_shift_plan():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    is_admin = current_user.role in ['admin', 'director']
    is_manager = current_user.profile and current_user.profile.subordinates
    can_view = is_admin or current_user.has_permission('view_shifts')
    
    if not (can_view or is_manager):
        flash('Permission denied.')
        return redirect(url_for('main.index'))

    # Get start date from args or default to current Monday
    start_date_str = request.args.get('start_date')
    if start_date_str:
        try:
            requested_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            # Sync to Monday of that week
            start_of_week = requested_date - timedelta(days=requested_date.weekday())
        except ValueError:
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
    else:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
    
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
    prev_week = start_of_week - timedelta(days=7)
    next_week = start_of_week + timedelta(days=7)
    
    # Get team members
    if is_admin:
        team_query = EmployeeProfile.query.filter_by(is_resigned=False)
    elif is_manager:
        team_query = EmployeeProfile.query.filter_by(manager_id=current_user.profile.id, is_resigned=False)
    else:
        team_query = EmployeeProfile.query.filter_by(department_id=current_user.profile.department_id, is_resigned=False)
        
    team_members = team_query.order_by(EmployeeProfile.first_name).all()
    member_ids = [m.id for m in team_members]
    
    # Fetch all shifts for the week for these members
    shifts = ShiftSchedule.query.filter(
        ShiftSchedule.employee_id.in_(member_ids),
        ShiftSchedule.date >= week_dates[0],
        ShiftSchedule.date <= week_dates[-1]
    ).all()
    
    # Organize: {member_id: {date: shift_type}}
    plan_data = {m.id: {d: None for d in week_dates} for m in team_members}
    for s in shifts:
        if s.employee_id in plan_data:
            plan_data[s.employee_id][s.date] = s.shift_type

        return render_template('admin/view_team_shift_plan.html',
                               title='Team Shift Plan',
                               team_members=team_members,
                               week_dates=week_dates,
                               plan_data=plan_data,
                               prev_week=prev_week,
                               next_week=next_week,
                               today=date.today())

# --- Data Management Routes ---

@bp.route('/admin/manage_data')
@admin_required
def manage_data():
    if current_user.role != 'admin':
        flash('Access denied. Only Admins can manage data.', 'danger')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/manage_data.html', title='Data Management')

@bp.route('/admin/data/clear_table', methods=['POST'])
@admin_required
def clear_table():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.dashboard'))

    table_name = request.form.get('table_name')
    if not table_name:
        flash('No table selected.', 'warning')
        return redirect(url_for('admin.manage_data'))

    # Map string to Model class safely
    models_map = {
        'Attendance': Attendance,
        'Leave': Leave,
        'ExpenseClaim': ExpenseClaim,
        'Payroll': Payroll,
        'Task': Task,
        'EmployeeTask': EmployeeTask,
        'AuditLog': AuditLog,
        'AssetHistory': AssetHistory,
        'Credit': Credit,
        'Debit': Debit,
        'Invoice': Invoice,
        'PurchaseOrder': PurchaseOrder,
        'BillEstimate': BillEstimate,
        'ShiftSchedule': ShiftSchedule,
        'JobOpening': JobOpening,
        'Candidate': Candidate,
        'Appraisal': Appraisal,
        'Vendor': Vendor,
        'Asset': Asset,
        'Holiday': Holiday,
        'Announcement': Announcement
    }

    model = models_map.get(table_name)
    if not model:
        flash(f'Invalid table: {table_name}', 'danger')
        return redirect(url_for('admin.manage_data'))

    try:
        # Delete all records
        num_deleted = db.session.query(model).delete()
        db.session.commit()

        log_audit('DELETE_ALL', table_name, None, f"Cleared {num_deleted} records from {table_name}", current_user)
        flash(f'Successfully deleted {num_deleted} records from {table_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing table: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_data'))

@bp.route('/admin/data/backup')
@admin_required
def backup_database():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        db_path = os.path.join(current_app.instance_path, 'app.db')
        if not os.path.exists(db_path):
            flash('Database file not found.', 'danger')
            return redirect(url_for('admin.manage_data'))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_genhr_{timestamp}.db"

        return send_file(
            db_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/x-sqlite3'
        )
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_data'))

@bp.route('/admin/data/restore', methods=['POST'])
@admin_required
def restore_database():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.dashboard'))
    if 'backup_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin.manage_data'))
    file = request.files['backup_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin.manage_data'))
    if file and file.filename.endswith('.db'):
        try:
            db_path = os.path.join(current_app.instance_path, 'app.db')
            if os.path.exists(db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safety_backup = os.path.join(current_app.instance_path, f"safety_backup_{timestamp}.db")
                shutil.copy2(db_path, safety_backup)
            filename = secure_filename(file.filename)
            temp_path = os.path.join(current_app.instance_path, f"temp_restore_{filename}")
            file.save(temp_path)
            db.session.remove()
            db.engine.dispose()
            if os.path.exists(db_path):
                os.remove(db_path)
            shutil.move(temp_path, db_path)
            log_audit('RESTORE', 'Database', None, f"Restored database from {filename}", current_user)
            flash('Database restored successfully. Please log in again.', 'success')
        except Exception as e:
            flash(f'Error restoring database: {str(e)}', 'danger')
    else:
        flash('Invalid file type. Please upload a .db file.', 'danger')
    return redirect(url_for('admin.manage_data'))

@bp.route('/admin/data/backup_full')
@admin_required
def backup_full():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"full_backup_genhr_{timestamp}.zip"

        temp_dir = tempfile.gettempdir()
        temp_zip_path = os.path.join(temp_dir, backup_filename)

        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            instance_path = current_app.instance_path
            if os.path.exists(instance_path):
                for root, dirs, files in os.walk(instance_path):
                    for file in files:
                        if not file.startswith('temp_restore_'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.join(instance_path, '..'))
                            zipf.write(file_path, arcname)

            docs_path = os.path.join(current_app.root_path, 'static', 'documents')
            if os.path.exists(docs_path):
                for root, dirs, files in os.walk(docs_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.join(current_app.root_path, '..'))
                        zipf.write(file_path, arcname)

            img_path = os.path.join(current_app.root_path, 'static', 'img')
            if os.path.exists(img_path):
                for root, dirs, files in os.walk(img_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.join(current_app.root_path, '..'))
                        zipf.write(file_path, arcname)

        return send_file(
            temp_zip_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/zip'
        )
    except Exception as e:
        flash(f'Error creating full backup: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_data'))

@bp.route('/admin/letter-head', methods=['GET', 'POST'])
@admin_required
def letter_head():
    form = LetterHeadForm()
    if form.validate_on_submit():
        sig = form.authorized_signature.data
        data = {
            'date': form.date.data.strftime('%d %B %Y'),
            'content': form.content.data,
            'signature_path': sig.file_path if sig else None,
            'signature_name': sig.name if sig else 'Authorized Signatory',
            'signature_designation': sig.designation if sig else ''
        }
        
        filename = generate_letter_head_pdf(data)
        return send_from_directory(directory='../instance', path=filename, as_attachment=True)
        
    return render_template('admin/letter_head.html', title='Letter Head', form=form)

@bp.route('/admin/assets/template')
@admin_required
def download_asset_template():
    vendors = [v.name for v in Vendor.query.all()]
    output = generate_asset_template(vendor_options=vendors)
    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=asset_template.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

@bp.route('/admin/assets/bulk_upload', methods=['POST'])
@admin_required
def bulk_upload_assets():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin.add_asset', tab='bulk'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin.add_asset', tab='bulk'))
    
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file)
            success_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    if pd.isna(row['Asset Name']) or pd.isna(row['Serial Number']):
                        continue
                    
                    if Asset.query.filter_by(serial_number=str(row['Serial Number'])).first():
                        errors.append(f"Row {index+2}: Serial {row['Serial Number']} exists")
                        continue
                    
                    vendor_name = row['Owned By'] if not pd.isna(row['Owned By']) else 'Gentize'
                    vendor = Vendor.query.filter_by(name=vendor_name).first()
                    
                    purchase_date = pd.to_datetime(row['Purchase Date (YYYY-MM-DD)']).date() if not pd.isna(row['Purchase Date (YYYY-MM-DD)']) else None
                    
                    asset = Asset(
                        name=row['Asset Name'],
                        category=row['Category'] if not pd.isna(row['Category']) else 'Laptop',
                        brand=row['Brand'] if not pd.isna(row['Brand']) else None,
                        model_name=row['Model Name'] if not pd.isna(row['Model Name']) else None,
                        serial_number=str(row['Serial Number']),
                        condition=row['Condition'] if not pd.isna(row['Condition']) else 'New',
                        status=row['Status'] if not pd.isna(row['Status']) else 'Available',
                        owned_by=vendor_name,
                        vendor_id=vendor.id if vendor else None,
                        purchase_date=purchase_date,
                        purchase_cost=float(row['Purchase Cost']) if not pd.isna(row['Purchase Cost']) else 0.0
                    )
                    
                    db.session.add(asset)
                    db.session.commit()
                    
                    # Initial History Log
                    history = AssetHistory(
                        asset_id=asset.id,
                        action='Created',
                        notes=f"Asset initialized via bulk upload. Status: {asset.status}",
                        performed_by=current_user.email
                    )
                    db.session.add(history)
                    db.session.commit()
                    
                    success_count += 1
                    
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Row {index+2}: {str(e)}")
            
            if success_count > 0:
                flash(f'Successfully uploaded {success_count} assets.', 'success')
            if errors:
                flash(f'Errors: {"; ".join(errors[:3])}...', 'warning')
                
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            
    return redirect(url_for('admin.add_asset', tab='bulk'))