import pandas as pd
import io
from openpyxl.worksheet.datavalidation import DataValidation

def export_attendance_to_excel(daily_records):
    
    attendance_data = []
    employee_summary = {}

    for record in daily_records:
        attendance_data.append({
            'Date': record['date'].strftime('%Y-%m-%d'),
            'Employee': f"{record['employee'].first_name} {record['employee'].last_name}",
            'Status': record['status'],
            'Check In': record['check_in'].strftime('%H:%M:%S') if record['check_in'] else 'N/A',
            'Check Out': record['check_out'].strftime('%H:%M:%S') if record['check_out'] else 'N/A',
            'No of Hours': record['hours']
        })

        employee_name = f"{record['employee'].first_name} {record['employee'].last_name}"
        summary = employee_summary.get(employee_name, {'hours': 0, 'days': 0})
        
        if record['status'] == 'Present':
            summary['hours'] += record['hours']
            if record['check_out']:
                summary['days'] += 1
        elif record['status'].startswith('On Leave'):
            summary['days'] += 1
        
        employee_summary[employee_name] = summary

    attendance_df = pd.DataFrame(attendance_data)

    summary_list = []
    for employee, summary in employee_summary.items():
        summary_list.append({
            'Employee': employee,
            'No of Hours': round(summary['hours'], 2),
            'No of Days': summary['days']
        })
    summary_df = pd.DataFrame(summary_list)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        attendance_df.to_excel(writer, index=False, sheet_name='Attendance')
        summary_df.to_excel(writer, index=False, sheet_name='Employee Summary')
    
    output.seek(0)
    
    return output

def export_assets_to_excel(assets):
    data = []
    for asset in assets:
        assigned = f"{asset.assigned_employee.first_name} {asset.assigned_employee.last_name}" if asset.assigned_employee else '-'
        data.append({
            'Asset Name': asset.name,
            'Category': asset.category,
            'Brand': asset.brand or '-',
            'Model': asset.model_name or '-',
            'Serial Number': asset.serial_number,
            'Condition': asset.condition,
            'Status': asset.status,
            'Assigned To': assigned,
            'Owned By': asset.owned_by,
            'Purchase Date': asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '-',
            'Purchase Cost': asset.purchase_cost or 0.0,
            'Warranty Expiry': asset.warranty_expiry.strftime('%Y-%m-%d') if asset.warranty_expiry else '-',
            'System Entry Date': asset.created_at.strftime('%Y-%m-%d')
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Assets')
    output.seek(0)
    return output

def export_employees_to_excel(employees):
    data = []
    for emp in employees:
        data.append({
            'Employee ID': emp.user.employeeid,
            'Prefix': emp.prefix,
            'First Name': emp.first_name,
            'Last Name': emp.last_name,
            'Email': emp.email,
            'Gender': emp.gender,
            'Marital Status': emp.marital_status,
            'Designation': emp.designation.title if emp.designation else '-',
            'Phone': emp.phone_number,
            'Address': emp.address,
            'Date of Birth': emp.date_of_birth.strftime('%Y-%m-%d') if emp.date_of_birth else '-',
            'Date of Joining': emp.date_of_joining.strftime('%Y-%m-%d') if emp.date_of_joining else '-',
            'Status': 'Resigned' if emp.is_resigned else 'Active',
            'Resigned Date': emp.resigned_date.strftime('%Y-%m-%d') if emp.resigned_date else '-',
            'Reports To': emp.reports_to or '-',
            'Experience': emp.years_of_experience,
            'Previous Employer': emp.previous_employer,
            'PAN': emp.pan_number,
            'Aadhar': emp.aadhar_number,
            'UAN': emp.uan_number,
            'PF No': emp.pf_number,
            'ESI No': emp.esi_number,
            'Emergency Contact': emp.emergency_contact,
            'Bank Name': emp.bank_name,
            'Account Number': emp.bank_account_number,
            'IFSC': emp.ifsc_code,
            'Branch': emp.branch
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Employees')
    output.seek(0)
    return output

def export_vendors_to_excel(vendors):
    data = []
    for v in vendors:
        data.append({
            'Vendor Name': v.name,
            'Category': v.category,
            'Contact Person': v.contact_person,
            'Email': v.email,
            'Phone': v.phone,
            'Status': v.status,
            'GSTIN': v.gstin or '-',
            'Payment Terms': v.payment_terms,
            'Bank Name': v.bank_name or '-',
            'Account No': v.bank_account or '-',
            'IFSC': v.ifsc_code or '-',
            'Contract Start': v.contract_start.strftime('%Y-%m-%d') if v.contract_start else '-',
            'Contract Expiry': v.contract_expiry.strftime('%Y-%m-%d') if v.contract_expiry else '-',
            'Services': v.services_provided,
            'Address': v.address
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendors')
    output.seek(0)
    return output

def generate_employee_template(designation_options=[], department_options=[]):
    columns = ['Prefix', 'First Name', 'Last Name', 'Email', 'Phone', 'Date of Birth (YYYY-MM-DD)', 
               'Date of Joining (YYYY-MM-DD)', 'Designation', 'Department', 'Gender', 'Marital Status', 
               'Address', 'PAN', 'Aadhar', 'UAN', 'PF No', 'ESI No', 'Bank Name', 'Account Number', 'IFSC', 'Branch',
               'Emergency Contact', 'Previous Employer', 'Years of Experience', 'Reports To']
    df = pd.DataFrame(columns=columns)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
        ws = writer.sheets['Template']
        
        # Prefix (Col A)
        dv_prefix = DataValidation(type="list", formula1='"Mr,Miss,Mrs"', allow_blank=True)
        ws.add_data_validation(dv_prefix)
        dv_prefix.add('A2:A1000')
        
        # Designation (Col H)
        if designation_options:
            options_df = pd.DataFrame({'Designation': designation_options})
            options_df.to_excel(writer, index=False, sheet_name='Options')
            count = len(designation_options) + 1
            dv_desig = DataValidation(type="list", formula1=f"'Options'!$A$2:$A${count}", allow_blank=True)
            ws.add_data_validation(dv_desig)
            dv_desig.add('H2:H1000')
            
        # Department (Col I)
        if department_options:
            dept_df = pd.DataFrame({'Department': department_options})
            dept_df.to_excel(writer, index=False, sheet_name='Departments')
            count = len(department_options) + 1
            dv_dept = DataValidation(type="list", formula1=f"'Departments'!$A$2:$A${count}", allow_blank=True)
            ws.add_data_validation(dv_dept)
            dv_dept.add('I2:I1000')
        
        # Gender (Col J)
        dv_gender = DataValidation(type="list", formula1='"Male,Female"', allow_blank=True)
        ws.add_data_validation(dv_gender)
        dv_gender.add('J2:J1000')
        
        # Marital Status (Col K)
        dv_marital = DataValidation(type="list", formula1='"Married,Single"', allow_blank=True)
        ws.add_data_validation(dv_marital)
        dv_marital.add('K2:K1000')
        
    output.seek(0)
    return output

def generate_asset_template(vendor_options=[]):
    columns = ['Asset Name', 'Category', 'Brand', 'Model Name', 'Serial Number', 
               'Condition', 'Status', 'Owned By', 'Purchase Date (YYYY-MM-DD)', 'Purchase Cost']
    df = pd.DataFrame(columns=columns)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
        ws = writer.sheets['Template']
        
        # Category (Col B)
        categories = "Laptop,Desktop,Mobile,Monitor,Keyboard,Mouse,Headset,Other"
        dv_cat = DataValidation(type="list", formula1=f'"{categories}"', allow_blank=True)
        ws.add_data_validation(dv_cat)
        dv_cat.add('B2:B1000')
        
        # Condition (Col F)
        conditions = "New,Good,Fair,Poor,Damaged"
        dv_cond = DataValidation(type="list", formula1=f'"{conditions}"', allow_blank=True)
        ws.add_data_validation(dv_cond)
        dv_cond.add('F2:F1000')
        
        # Status (Col G)
        statuses = "Available,Assigned,Under Repair,Broken,Lost"
        dv_status = DataValidation(type="list", formula1=f'"{statuses}"', allow_blank=True)
        ws.add_data_validation(dv_status)
        dv_status.add('G2:G1000')
        
        # Owned By (Col H)
        if vendor_options:
            options = ["Gentize"] + vendor_options
            options_df = pd.DataFrame({'Options': options})
            options_df.to_excel(writer, index=False, sheet_name='Options')
            count = len(options) + 1
            dv_owned = DataValidation(type="list", formula1=f"'Options'!$A$2:$A${count}", allow_blank=True)
            ws.add_data_validation(dv_owned)
            dv_owned.add('H2:H1000')
            
    output.seek(0)
    return output

def generate_holiday_template():
    columns = ['Holiday Name', 'Date (YYYY-MM-DD)', 'Description']
    df = pd.DataFrame(columns=columns)
    
    # Add dummy row
    df.loc[0] = ['Christmas Day', '2025-12-25', 'Public Holiday']
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    return output