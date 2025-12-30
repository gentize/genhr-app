from flask import render_template, flash, redirect, url_for, send_from_directory, request, make_response, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import extract
from employee_portal.admin.routes import admin_required
from employee_portal.utils.helpers import save_picture, save_file
from . import bp
from employee_portal import db
from employee_portal.main.forms import LeaveForm
from employee_portal.auth.forms import ExpenseClaimForm
from employee_portal.models import Attendance, Payroll, EmployeeProfile, Leave, User, Role, Appraisal, ExpenseClaim, Announcement, Holiday, EmployeeTask, ChatMessage
from employee_portal.excel import export_attendance_to_excel
from employee_portal.utils.helpers import utc_to_ist
from employee_portal.pdf import generate_payslip_pdf
import os
from datetime import date, datetime, timedelta
from functools import wraps

def employee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role in ['admin', 'director']:
            flash('You do not have permission to access this page.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/apply_expense', methods=['GET', 'POST'])
@login_required
@employee_required
def apply_expense():
    form = ExpenseClaimForm()
    if form.validate_on_submit():
        claim = ExpenseClaim(
            title=form.title.data,
            amount=form.amount.data,
            category=form.category.data,
            date_occurred=form.date_occurred.data,
            employee_id=current_user.profile.id
        )
        if form.receipt.data:
            receipt_file = save_file(form.receipt.data, folder='documents')
            claim.receipt_file = receipt_file
            
        db.session.add(claim)
        db.session.commit()
        flash('Your expense claim has been submitted.', 'success')
        return redirect(url_for('main.my_expenses'))
    return render_template('apply_expense.html', title='Apply for Expense Reimbursement', form=form)

@bp.route('/my_expenses')
@login_required
def my_expenses():
    if not current_user.profile:
        return redirect(url_for('main.index'))
    claims = ExpenseClaim.query.filter_by(employee_id=current_user.profile.id).order_by(ExpenseClaim.applied_date.desc()).all()
    return render_template('my_expenses.html', claims=claims, title='My Expense Claims')

@bp.route('/my_appraisals')
@login_required
def my_appraisals():
    if not current_user.profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('main.index'))
    
    appraisals = Appraisal.query.filter_by(employee_id=current_user.profile.id, status='Finalized').order_by(Appraisal.appraisal_date.desc()).all()
    return render_template('my_appraisals.html', appraisals=appraisals, title='My Appraisals')

@bp.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'image' in request.files:
        image = request.files['image']
        if image.filename != '':
            picture_file = save_picture(image)
            current_user.profile.image_file = picture_file
            db.session.commit()
            flash('Your profile picture has been updated!', 'success')
        else:
            flash('No image selected!', 'danger')
    else:
        flash('No image part in the form!', 'danger')
    return redirect(url_for('main.profile'))

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    if current_user.is_authenticated:
        # For the dashboard, we need today's date and assigned tasks
        from employee_portal.models import EmployeeTask, Announcement, Holiday, Attendance
        today = date.today()
        assigned_tasks = []
        todays_attendance = None
        attendance_records = []
        image_file = url_for('static', filename='img/default.jpg')

        if current_user.profile:
            assigned_tasks = EmployeeTask.query.filter_by(employee_id=current_user.profile.id).all()
            todays_attendance = Attendance.query.filter(
                db.and_(
                    Attendance.employee_id == current_user.profile.id,
                    db.func.date(Attendance.check_in) == today
                )
            ).order_by(Attendance.check_in.desc()).first()
            attendance_records = current_user.profile.attendances.order_by(Attendance.check_in.desc()).limit(10).all()
            
            if current_user.profile.image_file:
                image_file = url_for('static', filename='img/' + current_user.profile.image_file)
        
        announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.date_posted.desc()).limit(3).all()
        holidays = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date.asc()).limit(3).all()
        
        # Check if Admin/Director
        is_leadership = current_user.role in ['admin', 'director']
        
        # if is_leadership:
        #     return redirect(url_for('admin.dashboard'))
        return render_template('profile.html', today=today, assigned_tasks=assigned_tasks, todays_attendance=todays_attendance, attendance_records=attendance_records, image_file=image_file, announcements=announcements, holidays=holidays)
    return render_template('index.html')

@bp.route('/profile')
@login_required
def profile():
    from employee_portal.models import Announcement, Holiday, EmployeeTask
    todays_attendance = None
    attendance_records = []
    assigned_tasks = []
    image_file = url_for('static', filename='img/default.jpg')
    today = date.today()

    if current_user.profile:
        todays_attendance = Attendance.query.filter(
            db.and_(
                Attendance.employee_id == current_user.profile.id,
                db.func.date(Attendance.check_in) == today
            )
        ).order_by(Attendance.check_in.desc()).first()
        
        attendance_records = current_user.profile.attendances.order_by(Attendance.check_in.desc()).limit(10).all()
        assigned_tasks = EmployeeTask.query.filter_by(employee_id=current_user.profile.id).all()
        
        if current_user.profile.image_file:
            image_file = url_for('static', filename='img/' + current_user.profile.image_file)

        # Check for Task Proximity Warnings (Target Date N and N-1)
        for task in assigned_tasks:
            if task.status != 'Completed' and task.master_task.target_date:
                target = task.master_task.target_date
                today_dt = date.today()
                
                # N is today, N-1 is tomorrow (so today is one day before target)
                days_diff = (target - today_dt).days
                
                if days_diff == 0:
                    flash(f'Urgent: Task {task.master_task.task_no or "T-"+str(task.master_task.id)} target date is today!', 'danger')
                elif days_diff == 1:
                    flash(f'Warning: Task {task.master_task.task_no or "T-"+str(task.master_task.id)} is due tomorrow.', 'warning')
                elif days_diff < 0:
                    flash(f'Notice: Task {task.master_task.task_no or "T-"+str(task.master_task.id)} target date has passed.', 'info')
    
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.date_posted.desc()).limit(3).all()
    holidays = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date.asc()).limit(3).all()

    return render_template('profile.html', todays_attendance=todays_attendance, attendance_records=attendance_records, assigned_tasks=assigned_tasks, image_file=image_file, today=today, announcements=announcements, holidays=holidays)

@bp.route('/task/<int:task_id>/details')
@login_required
def view_task_details(task_id):
    from employee_portal.models import EmployeeTask
    task = EmployeeTask.query.get_or_404(task_id)
    
    # Permission check: User must be the owner, or an admin/director
    is_owner = current_user.profile and task.employee_id == current_user.profile.id
    is_leadership = current_user.role in ['admin', 'director']
    
    if not (is_owner or is_leadership):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.profile'))

    return render_template('task_details_employee.html', task=task, title=f"Task {task.master_task.task_no or task.id}")

@bp.route('/task/update_status/<int:task_id>', methods=['POST'])
@login_required
def update_task_status(task_id):
    from employee_portal.models import EmployeeTask
    task = EmployeeTask.query.get_or_404(task_id)
    
    # Permission: Owner, Manager, Admin, Director
    is_owner = current_user.profile and task.employee_id == current_user.profile.id
    is_admin = current_user.role == 'admin'
    is_director = current_user.role == 'director'
    is_manager = current_user.profile and task.employee.reports_to_id == current_user.profile.id
    
    if not (is_owner or is_admin or is_director or is_manager):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.profile'))

    new_status = request.form.get('status')
    reason = request.form.get('reason', '')
    f_date_str = request.form.get('followup_date')

    task.status = new_status
    task.reason = reason
    
    if new_status in ['Completed', 'Rejected']:
        task.followup_date = None
        if new_status == 'Completed':
            task.is_completed = True
            task.completed_at = datetime.utcnow()
            task.completed_by = current_user.email
    else:
        task.is_completed = False
        task.completed_at = None
        if f_date_str:
            task.followup_date = datetime.strptime(f_date_str, '%Y-%m-%d').date()

    # Sync status to Master Task if it's a direct 1:1 assignment
    # This fulfills the requirement: "what ever the assigned employee seleted the status that should be displayed in Task Ticket status"
    if task.master_task.task_add_to_id:
        task.master_task.status = new_status

    db.session.commit()
    flash(f'Task "{task.master_task.description}" updated to {new_status}.', 'success')
    return redirect(request.referrer or url_for('main.profile'))

@bp.route('/api/search_colleagues')
@login_required
def search_colleagues_api():
    query_str = request.args.get('q', '').strip()
    if not query_str:
        return jsonify([])
    
    query = EmployeeProfile.query.join(User).join(Role).filter(
        EmployeeProfile.is_resigned == False,
        db.or_(
            EmployeeProfile.first_name.ilike(f'%{query_str}%'),
            EmployeeProfile.last_name.ilike(f'%{query_str}%'),
            User.employeeid.ilike(f'%{query_str}%'),
            Role.name.ilike(f'%{query_str}%'),
            db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name).ilike(f'%{query_str}%'),
            db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name, ' (', User.employeeid, ') - ', Role.name).ilike(f'%{query_str}%')
        )
    ).limit(10)
    
    results = []
    for emp in query.all():
        role_name = emp.user.user_role.name if emp.user.user_role else 'No Role'
        results.append({
            'name': f"{emp.first_name} {emp.last_name} ({emp.user.employeeid}) - {role_name}",
            'id': emp.id
        })
    return jsonify(results)

@bp.route('/directory')
@login_required
def directory():
    search_query = request.args.get('search_query', '')
    # List all active employees (exclude resigned)
    query = EmployeeProfile.query.join(User).join(Role).filter(
        Role.name != 'Admin',
        EmployeeProfile.is_resigned == False
    )

    if search_query:
        term = search_query.strip()
        query = query.filter(
            db.or_(
                EmployeeProfile.first_name.ilike(f'%{term}%'),
                EmployeeProfile.last_name.ilike(f'%{term}%'),
                User.employeeid.ilike(f'%{term}%'),
                Role.name.ilike(f'%{term}%'),
                db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name).ilike(f'%{term}%'),
                db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name, ' (', User.employeeid, ')').ilike(f'%{term}%'),
                db.func.concat(EmployeeProfile.first_name, ' ', EmployeeProfile.last_name, ' (', User.employeeid, ') - ', Role.name).ilike(f'%{term}%')
            )
        )
    
    employees = query.all()
    return render_template('directory.html', employees=employees, search_query=search_query)

@bp.route('/directory/<int:profile_id>')
@login_required
def view_colleague(profile_id):
    employee = EmployeeProfile.query.get_or_404(profile_id)
    image_file = url_for('static', filename='img/' + (employee.image_file or 'default.jpg'))
    return render_template('directory_profile.html', employee=employee, image_file=image_file)

@bp.route('/api/org_chart')
@login_required
def org_chart_api():
    employees = set()
    if current_user.role in ['admin', 'director']:
        all_emps = EmployeeProfile.query.filter_by(is_resigned=False).all()
        employees.update(all_emps)
    elif current_user.profile:
        me = current_user.profile
        employees.add(me)
        
        # Add Ancestors
        curr = me
        while curr.manager:
            curr = curr.manager
            employees.add(curr)
            
        # Add Direct Subordinates
        for sub in me.subordinates:
            employees.add(sub)
            
        # Add All Directors (to ensure top level is visible)
        directors = EmployeeProfile.query.join(User).join(Role).filter(Role.name == 'Director', EmployeeProfile.is_resigned == False).all()
        for d in directors:
            employees.add(d)
        
    employees = list(employees)
    employee_ids = {str(e.id) for e in employees}
    
    data = []
    
    for emp in employees:
        node_id = str(emp.id)
        raw_parent_id = str(emp.reports_to_id) if emp.reports_to_id else ''
        
        # If parent is not in our filtered list, treat as root for this chart
        if raw_parent_id and raw_parent_id not in employee_ids:
            parent_id = ''
        else:
            parent_id = raw_parent_id

        role = emp.designation.title if emp.designation else (emp.user.user_role.name if emp.user.user_role else 'Employee')
        name = f"{emp.first_name} {emp.last_name}"
        image_url = url_for('static', filename='img/' + (emp.image_file or 'default.jpg'))
        profile_url = url_for('main.view_colleague', profile_id=emp.id, source='orgchart')
        
        content = f'<div class="org-node-card">' \
                  f'<a href="{profile_url}" class="text-decoration-none text-dark d-block">' \
                  f'<img src="{image_url}" class="rounded-circle mb-2" width="50" height="50" style="object-fit: cover;">' \
                  f'<div class="fw-bold text-truncate" style="max-width: 140px; margin: 0 auto;">{name}</div>' \
                  f'<div class="text-muted small text-truncate" style="max-width: 140px; margin: 0 auto;">{role}</div>' \
                  f'</a>' \
                  f'</div>'
        
        data.append([{
            'v': node_id,
            'f': content
        }, parent_id, role])
        
    return jsonify(data)

@bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html', title='Settings')

@bp.route('/apply_leave', methods=['GET', 'POST'])
@login_required
@employee_required
def apply_leave():
    form = LeaveForm()
    if form.validate_on_submit():
        leave = Leave(
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
            leave_type=form.leave_type.data,
            employee_id=current_user.profile.id
        )
        db.session.add(leave)
        db.session.commit()
        flash('Your leave application has been submitted.', 'success')
        return redirect(url_for('main.profile'))
    return render_template('apply_leave.html', title='Apply for Leave', form=form)

@bp.route('/leave_requests')
@login_required
def leave_requests():
    leaves = []
    if current_user.role == 'admin':
        leaves = Leave.query.filter_by(status='Pending').all()
    elif current_user.profile:
        full_name = f"{current_user.profile.first_name} {current_user.profile.last_name}"
        leaves = Leave.query.join(EmployeeProfile).filter(
            Leave.status == 'Pending',
            EmployeeProfile.reports_to == full_name
        ).all()
    
    return render_template('leave_requests.html', leaves=leaves, title='Leave Requests')

@bp.route('/leave_action/<int:leave_id>/<string:action>', methods=['POST'])
@login_required
def leave_action(leave_id, action):
    leave = Leave.query.get_or_404(leave_id)
    
    # Permission Check
    is_authorized = False
    if current_user.role == 'admin':
        is_authorized = True
    elif current_user.profile:
        full_name = f"{current_user.profile.first_name} {current_user.profile.last_name}"
        if leave.employee.reports_to == full_name:
            is_authorized = True
            
    if not is_authorized:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.index'))

    if action == 'approve':
        leave.status = 'Approved'
        approver = f"{current_user.profile.first_name} {current_user.profile.last_name}" if current_user.profile else 'Admin'
        leave.approved_by = approver
        flash('Leave request approved.', 'success')
    elif action == 'reject':
        leave.status = 'Rejected'
        approver = f"{current_user.profile.first_name} {current_user.profile.last_name}" if current_user.profile else 'Admin'
        leave.approved_by = approver
        leave.rejection_reason = request.form.get('reason', '')
        flash('Leave request rejected.', 'warning')
    
    db.session.commit()
    return redirect(url_for('main.leave_requests'))

@bp.route('/attendance_action', methods=['POST'])
@login_required
def attendance_action():
    if not current_user.profile:
        return jsonify({'success': False, 'message': 'Profile not found.'}), 400
        
    today = date.today()
    # Find the latest check-in for the user for today
    todays_attendance = Attendance.query.filter(
        db.and_(
            Attendance.employee_id == current_user.profile.id,
            db.func.date(Attendance.check_in) == today
        )
    ).order_by(Attendance.check_in.desc()).first()

    message = ""
    if todays_attendance and todays_attendance.check_out is None:
        # User is checking out
        todays_attendance.check_out = datetime.utcnow()
        db.session.commit()
        message = 'Thanks for your hard work! See you tomorrow!'
    elif todays_attendance and todays_attendance.check_out is not None:
        # User has already checked in and out for the day
        return jsonify({'success': False, 'message': 'You have already completed your attendance for today.'}), 400
    else:
        # User is checking in
        attendance = Attendance(employee_id=current_user.profile.id)
        db.session.add(attendance)
        db.session.commit()
        message = 'Welcome! Have a productive day!'
        
    return jsonify({'success': True, 'message': message})

@bp.route('/my_payslips')
@login_required
def my_payslips():
    if not current_user.profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('main.index'))
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    query = Payroll.query.filter_by(employee_id=current_user.profile.id)
    
    if month:
        query = query.filter(extract('month', Payroll.pay_period_end) == month)
    if year:
        query = query.filter(extract('year', Payroll.pay_period_end) == year)
        
    payslips = query.order_by(Payroll.pay_period_end.desc()).all()
    
    # Get available years for the filter
    available_years = db.session.query(extract('year', Payroll.pay_period_end)).filter_by(employee_id=current_user.profile.id).distinct().all()
    years = sorted([int(y[0]) for y in available_years], reverse=True)
    
    return render_template('my_payslips.html', payslips=payslips, years=years, selected_month=month, selected_year=year, title='My Payslips')

@bp.route('/download_payslip/<int:payroll_id>')
@login_required
def download_payslip(payroll_id):
    payroll = Payroll.query.get_or_404(payroll_id)
    
    # Permission: Either the employee themselves OR an Admin
    is_owner = current_user.profile and (payroll.employee_id == current_user.profile.id)
    is_admin = current_user.role == 'admin'
    
    if not (is_owner or is_admin):
        flash('You are not authorized to view this payslip.', 'danger')
        return redirect(url_for('main.profile'))
    
    pdf_file = generate_payslip_pdf(payroll)
    
    # Custom filename: Payslip_FirstNameLastName_MonthYear.pdf
    month_year = payroll.pay_period_end.strftime('%B%Y')
    safe_name = f"{payroll.employee.first_name}{payroll.employee.last_name}"
    download_filename = f"Payslip_{safe_name}_{month_year}.pdf"
    
    # Use absolute path to the instance folder
    instance_dir = os.path.join(current_app.root_path, '..', 'instance')
    
    return send_from_directory(
        instance_dir,
        pdf_file,
        as_attachment=True,
        download_name=download_filename
    )

@bp.route('/get_attendance_status')
@login_required
def get_attendance_status():
    if not current_user.profile:
        return jsonify({'is_checked_in': False, 'is_checked_out': False})
    
    today = date.today()
    record = Attendance.query.filter(
        db.and_(
            Attendance.employee_id == current_user.profile.id,
            db.func.date(Attendance.check_in) == today
        )
    ).order_by(Attendance.check_in.desc()).first()
    
    status = {
        'is_checked_in': record is not None,
        'is_checked_out': record.check_out is not None if record else False
    }
    return jsonify(status)

@bp.route('/api/holidays')
@login_required
def get_holidays_api():
    from employee_portal.models import Holiday
    holidays = Holiday.query.all()
    holiday_list = []
    for h in holidays:
        holiday_list.append({
            'date': h.date.strftime('%Y-%m-%d'),
            'name': h.name
        })
    return jsonify(holiday_list)

@bp.route('/calendar')
@login_required
def view_calendar():
    return render_template('calendar.html', title='Company Calendar')

@bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@admin_required
def attendance():
    # Only show employees who haven't fully resigned yet
    employees = [e for e in EmployeeProfile.query.all() if not e.is_effectively_resigned]
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        from_date_str = request.form.get('from_date')
        to_date_str = request.form.get('to_date')
    else:
        employee_id = None
        from_date_str = date.today().strftime('%Y-%m-%d')
        to_date_str = date.today().strftime('%Y-%m-%d')

    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else None
    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None

    # --- Data fetching ---
    attendance_query = Attendance.query
    leave_query = Leave.query
    if employee_id:
        attendance_query = attendance_query.filter(Attendance.employee_id == employee_id)
        leave_query = leave_query.filter(Leave.employee_id == employee_id)
    if from_date:
        attendance_query = attendance_query.filter(db.func.date(Attendance.check_in) >= from_date)
        leave_query = leave_query.filter(Leave.end_date >= from_date)
    if to_date:
        attendance_query = attendance_query.filter(db.func.date(Attendance.check_in) <= to_date)
        leave_query = leave_query.filter(Leave.start_date <= to_date)
        
    attendance_records = attendance_query.all()
    leave_records = leave_query.all()

    # --- Data merging ---
    daily_records = {}
    for record in attendance_records:
        if not record.employee or not record.check_in:
            continue
        key = (record.employee_id, record.check_in.date())
        if key not in daily_records:
            daily_records[key] = {
                'employee': record.employee,
                'date': record.check_in.date(),
                'status': 'Present',
                'check_in': record.check_in,
                'check_out': record.check_out,
                'hours': 0,
            }
        if record.check_out and (daily_records[key]['check_out'] is None or record.check_out > daily_records[key]['check_out']):
             daily_records[key]['check_out'] = record.check_out

    for record in leave_records:
        if not record.employee:
            continue
        
        current_day = record.start_date
        while current_day <= record.end_date:
            if (from_date and current_day < from_date) or (to_date and current_day > to_date):
                current_day += timedelta(days=1)
                continue
                
            key = (record.employee_id, current_day)
            daily_records[key] = {
                'employee': record.employee,
                'date': current_day,
                'status': f"On Leave ({record.leave_type})",
                'check_in': None,
                'check_out': None,
                'hours': 0
            }
            current_day += timedelta(days=1)

    # --- Calculations ---
    employee_summary = {}
    final_records = sorted(daily_records.values(), key=lambda r: (r['date'], r['employee'].id), reverse=True)
    
    for record in final_records:
        employee_name = f"{record['employee'].first_name} {record['employee'].last_name}"
        summary = employee_summary.get(employee_name, {'hours': 0, 'days': 0})
        
        if record['status'] == 'Present' and record['check_out']:
            duration = record['check_out'] - record['check_in']
            hours = duration.total_seconds() / 3600
            record['hours'] = round(hours, 2)
            summary['hours'] += hours
            summary['days'] += 1
        elif record['status'].startswith('On Leave'):
             summary['days'] +=1

        employee_summary[employee_name] = summary


    return render_template('attendance.html', employees=employees, attendances=final_records, employee_summary=employee_summary, from_date=from_date_str, to_date=to_date_str, title="Attendance")

@bp.route('/export_attendance')
@login_required
@admin_required
def export_attendance():
    employee_id = request.args.get('employee_id')
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')

    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else None
    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None

    # --- Data fetching ---
    attendance_query = Attendance.query
    leave_query = Leave.query
    if employee_id:
        attendance_query = attendance_query.filter(Attendance.employee_id == employee_id)
        leave_query = leave_query.filter(Leave.employee_id == employee_id)
    if from_date:
        attendance_query = attendance_query.filter(db.func.date(Attendance.check_in) >= from_date)
        leave_query = leave_query.filter(Leave.end_date >= from_date)
    if to_date:
        attendance_query = attendance_query.filter(db.func.date(Attendance.check_in) <= to_date)
        leave_query = leave_query.filter(Leave.start_date <= to_date)
        
    attendance_records = attendance_query.all()
    leave_records = leave_query.all()

    # --- Data merging ---
    daily_records = {}
    for record in attendance_records:
        if not record.employee or not record.check_in:
            continue
        key = (record.employee_id, record.check_in.date())
        if key not in daily_records:
            daily_records[key] = {
                'employee': record.employee,
                'date': record.check_in.date(),
                'status': 'Present',
                'check_in': record.check_in,
                'check_out': record.check_out,
                'hours': 0,
            }
        if record.check_out and daily_records[key]['check_out'] is None:
             daily_records[key]['check_out'] = record.check_out

    for record in leave_records:
        if not record.employee:
            continue
        
        current_day = record.start_date
        while current_day <= record.end_date:
            if (from_date and current_day < from_date) or (to_date and current_day > to_date):
                current_day += timedelta(days=1)
                continue
                
            key = (record.employee_id, current_day)
            daily_records[key] = {
                'employee': record.employee,
                'date': current_day,
                'status': f"On Leave ({record.leave_type})",
                'check_in': None,
                'check_out': None,
                'hours': 0
            }
            current_day += timedelta(days=1)

    # --- Calculations ---
    final_records = sorted(daily_records.values(), key=lambda r: (r['date'], r['employee'].id), reverse=True)
    
    for record in final_records:
        if record['status'] == 'Present' and record['check_out']:
            duration = record['check_out'] - record['check_in']
            hours = duration.total_seconds() / 3600
            record['hours'] = round(hours, 2)

    output = export_attendance_to_excel(final_records)

    return make_response(output, 200, {
        'Content-Disposition': 'attachment; filename=attendance.xlsx',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

# --- Chat Routes ---

@bp.route('/chat')
@login_required
def chat():
    if not current_user.profile:
        flash('You must have an employee profile to use chat.', 'warning')
        return redirect(url_for('main.index'))

    # List all colleagues for the sidebar
    colleagues = EmployeeProfile.query.filter(
        EmployeeProfile.id != current_user.profile.id,
        EmployeeProfile.is_resigned == False
    ).order_by(EmployeeProfile.first_name).all()
    
    # Calculate unread counts
    unread_counts = db.session.query(
        ChatMessage.sender_id, db.func.count(ChatMessage.id)
    ).filter(
        ChatMessage.recipient_id == current_user.profile.id,
        ChatMessage.is_read == False
    ).group_by(ChatMessage.sender_id).all()
    
    unread_map = {uid: count for uid, count in unread_counts}
    
    for c in colleagues:
        c.unread = unread_map.get(c.id, 0)
    
    recipient_id = request.args.get('recipient_id', type=int)
    recipient = None
    if recipient_id:
        recipient = EmployeeProfile.query.get_or_404(recipient_id)
        
    return render_template('chat.html', colleagues=colleagues, recipient=recipient, title='Chat')

@bp.route('/api/chat/history/<int:recipient_id>')
@login_required
def chat_history(recipient_id):
    messages = ChatMessage.query.filter(
        db.or_(
            db.and_(ChatMessage.sender_id == current_user.profile.id, ChatMessage.recipient_id == recipient_id),
            db.and_(ChatMessage.sender_id == recipient_id, ChatMessage.recipient_id == current_user.profile.id)
        )
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    # Mark messages as read
    unread = ChatMessage.query.filter_by(sender_id=recipient_id, recipient_id=current_user.profile.id, is_read=False).all()
    for m in unread:
        m.is_read = True
    db.session.commit()
    
    return jsonify([{
        'id': m.id,
        'body': m.body,
        'sender_id': m.sender_id,
        'timestamp': utc_to_ist(m.timestamp).strftime('%H:%M'),
        'is_mine': m.sender_id == current_user.profile.id
    } for m in messages])

@bp.route('/api/chat/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    recipient_id = data.get('recipient_id')
    body = data.get('body')
    
    if not recipient_id or not body:
        return jsonify({'success': False}), 400
        
    message = ChatMessage(
        sender_id=current_user.profile.id,
        recipient_id=recipient_id,
        body=body
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'body': message.body,
            'timestamp': utc_to_ist(message.timestamp).strftime('%H:%M')
        }
    })

@bp.route('/api/chat/unread_count')
@login_required
def unread_count():
    if not current_user.profile:
        return jsonify({'count': 0})
        
    is_detailed = request.args.get('detailed') == 'true'
    
    if is_detailed:
        breakdown_query = db.session.query(
            ChatMessage.sender_id, db.func.count(ChatMessage.id)
        ).filter(
            ChatMessage.recipient_id == current_user.profile.id,
            ChatMessage.is_read == False
        ).group_by(ChatMessage.sender_id).all()
        
        breakdown = {uid: count for uid, count in breakdown_query}
        total_count = sum(breakdown.values())
        return jsonify({'count': total_count, 'breakdown': breakdown})
    
    count = ChatMessage.query.filter_by(recipient_id=current_user.profile.id, is_read=False).count()
    return jsonify({'count': count})
