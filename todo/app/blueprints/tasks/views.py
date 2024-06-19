from app import  db
# Import the forms
from .forms import TaskForm, UpdateTaskForm
# Import the Models
from app.models import Task, User
from flask import flash, redirect, render_template, request, url_for, Blueprint
# Import 
from flask_login import current_user, login_required

tasks = Blueprint("tasks", __name__)


@tasks.route("/all_tasks")
@login_required
def all_tasks():
    tasks = User.query.filter_by(username=current_user.username).first().tasks
    return render_template('all_tasks.html', title='All Tasks', tasks=tasks)


@tasks.route("/add_task", methods=['POST', 'GET'])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(content=form.task_name.data, author=current_user)
        db.session.add(task)
        db.session.commit()
        flash('Task Created', 'success')
        return redirect(url_for('tasks.add_task'))
    return render_template('add_task.html', form=form, title='Add Task')


@tasks.route("/all_tasks/<int:task_id>/update_task", methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    form = UpdateTaskForm()
    if form.validate_on_submit():
        if form.task_name.data != task.content:
            task.content = form.task_name.data
            db.session.commit()
            flash('Task Updated', 'success')
            return redirect(url_for('all_tasks'))
        else:
            flash('No Changes Made', 'warning')
            return redirect(url_for('tasks.all_tasks'))
    elif request.method == 'GET':
        form.task_name.data = task.content
    return render_template('add_task.html', title='Update Task', form=form)


@tasks.route("/all_tasks/<int:task_id>/delete_task")
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task Deleted', 'info')
    return redirect(url_for('tasks.all_tasks'))
