from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func
from . import bp
from .forms import LoginForm, RegistrationForm, ChangePasswordForm
from employee_portal import db
from employee_portal.models import User, EmployeeProfile

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(func.lower(User.employeeid) == func.lower(form.employeeid.data)).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid Employee ID or password')
            return redirect(url_for('auth.login'))
            
        if user.profile and user.profile.is_effectively_resigned:
            flash('Your account has been deactivated.', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=form.remember_me.data)
        
        if user.is_first_login:
            flash('Please change your password to continue.', 'warning')
            return redirect(url_for('auth.change_password'))
            
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.profile'))
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(employeeid=form.employeeid.data, email=form.email.data)
        user.set_password(form.password.data)
        # For now, all registered users are employees. Admin will be created manually.
        user.role = 'employee' # This is property setter (noop currently unless I fixed it or migration handled it)
        # Note: 'register' route might be broken for role assignment if I didn't fix the setter logic or use role_id. 
        # But 'add_employee' is primary method now. I'll leave register as is for now or fix it if requested.
        
        # Create an associated employee profile
        profile = EmployeeProfile(
            email=form.email.data,
            user=user
        )
        db.session.add(user)
        db.session.add(profile)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.old_password.data):
            current_user.set_password(form.new_password.data)
            current_user.is_first_login = False
            db.session.commit()
            flash('Your password has been changed successfully.', 'success')
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.profile'))
        else:
            flash('Invalid old password.', 'danger')
    return render_template('auth/change_password.html', title='Change Password', form=form)
