import os
import secrets
from PIL import Image
from flask import current_app

from datetime import datetime, timedelta

def utc_to_ist(utc_dt):
    if not utc_dt:
        return None
    return utc_dt + timedelta(hours=5, minutes=30)

def format_datetime_ist(utc_dt, fmt='%Y-%m-%d %H:%M:%S'):
    if not utc_dt:
        return ''
    ist_dt = utc_to_ist(utc_dt)
    return ist_dt.strftime(fmt)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/img', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

def save_file(form_file, folder='documents'):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_file.filename)
    file_fn = random_hex + f_ext
    file_path = os.path.join(current_app.root_path, 'static', folder, file_fn)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    form_file.save(file_path)
    return file_fn

def log_audit(action, resource_type, resource_id, details, user):
    """
    Logs a system action to the AuditLog table.
    user: The User model instance performing the action.
    """
    from employee_portal import db
    from employee_portal.models import AuditLog

    performed_by = user.email if user and user.email else "System/Unknown"
    
    log = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        performed_by=performed_by
    )
    db.session.add(log)
    # Note: We don't commit here usually to allow wrapping in larger transactions,
    # but for audit logs, we often want them even if the main transaction fails (if possible),
    # but with SQLAlchemy session it's tied. We'll rely on the caller to commit or 
    # we can commit here if it's a standalone action. 
    # For safety in existing flows, I will NOT commit here, relying on the main route to commit.
    # EDIT: Actually, explicit commit is safer for logs to ensure they persist.
    try:
        db.session.commit()
    except Exception as e:
        print(f"Failed to write audit log: {e}")
        db.session.rollback()

def get_vendors():
    from employee_portal.models import Vendor
    return Vendor.query.all()