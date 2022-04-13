
from flask_wtf import FlaskForm
from wtforms.fields import DateField
from wtforms import validators, SubmitField


class InfoForm(FlaskForm):
    startDate = DateField('Start Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    endDate = DateField('End Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    submit = SubmitField('Submit')
    