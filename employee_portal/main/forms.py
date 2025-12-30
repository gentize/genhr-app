from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SelectField, SubmitField
from wtforms.validators import DataRequired

class LeaveForm(FlaskForm):
    start_date = DateField('From Date', validators=[DataRequired()])
    end_date = DateField('To Date', validators=[DataRequired()])
    reason = StringField('Reason')
    leave_type = SelectField('Leave Type', choices=[('Sick', 'Sick'), ('Casual', 'Casual'), ('Vacation', 'Vacation')], validators=[DataRequired()])
    submit = SubmitField('Apply')
