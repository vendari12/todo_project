# Import the User Database Model
from flask_wtf import FlaskForm
# Form Fields
from wtforms import  StringField, SubmitField
# Form Validators for Form fields
from wtforms.validators import DataRequired



class TaskForm(FlaskForm):
    task_name = StringField(label='Task Description', validators=[DataRequired()])
    submit = SubmitField(label='Add Task')

class UpdateTaskForm(FlaskForm):
    task_name = StringField(label='Update Task Description', validators=[DataRequired()])
    submit = SubmitField(label='Save Changes')
