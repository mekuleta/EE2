from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
import pandas as pd
import datetime
import os

# Initialize the Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    body_part = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer)
    hold = db.Column(db.Integer)
    total_time = db.Column(db.Integer, nullable=False)
    equipment = db.Column(db.String(150))
    state = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    space = db.Column(db.String(50))
    directions = db.Column(db.Text, nullable=False)
    added_by = db.Column(db.String(50))

class ExerciseDone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('exercise'))
        else:
            flash('Login failed. Check your email and password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/exercise', methods=['GET', 'POST'])
def exercise():
    if request.method == 'POST':
        body_part = request.form.get('body_part')
        type = request.form.get('type')
        time_available = int(request.form.get('time_available'))
        equipment = request.form.getlist('equipment')
        difficulty = request.form.getlist('difficulty')
        space = request.form.get('space')

        exercises = Exercise.query.filter_by(body_part=body_part, type=type).all()

        selected_exercises = exercises[:5]

        if current_user.is_authenticated:
            user_id = current_user.id
            past_exercises = ExerciseDone.query.filter_by(user_id=user_id).order_by(ExerciseDone.timestamp.desc()).all()
            past_exercise_ids = [ex.exercise_id for ex in past_exercises]

            selected_exercises = [ex for ex in exercises if ex.id not in past_exercise_ids][:5]

        return render_template('routine_proposal.html', exercises=selected_exercises)

    return render_template('exercise_now.html')

@app.route('/routine_proposal', methods=['POST'])
@login_required
def routine_proposal():
    user_id = current_user.id
    exercise_ids = request.form.getlist('exercise_id')

    for exercise_id in exercise_ids:
        new_exercise_done = ExerciseDone(user_id=user_id, exercise_id=exercise_id, timestamp=datetime.datetime.now())
        db.session.add(new_exercise_done)
    db.session.commit()

    flash('Exercises marked as completed!', 'success')
    return redirect(url_for('track_record'))

@app.route('/track_record')
@login_required
def track_record():
    user_id = current_user.id
    exercises_done = ExerciseDone.query.filter_by(user_id=user_id).all()
    return render_template('track_record.html', exercises_done=exercises_done)

@app.route('/add_exercise', methods=['GET', 'POST'])
@login_required
def add_exercise():
    if request.method == 'POST':
        name = request.form.get('name')
        body_part = request.form.get('body_part')
        type = request.form.get('type')
        sets = request.form.get('sets')
        reps = request.form.get('reps')
        hold = request.form.get('hold')
        total_time = request.form.get('total_time')
        equipment = request.form.get('equipment')
        state = request.form.get('state')
        level = request.form.get('level')
        space = request.form.get('space')
        directions = request.form.get('directions')

        new_exercise = Exercise(name=name, body_part=body_part, type=type, sets=sets, reps=reps, hold=hold,
                                total_time=total_time, equipment=equipment, state=state, level=level, space=space, 
                                directions=directions, added_by='user')
        db.session.add(new_exercise)
        db.session.commit()
        flash('Exercise added successfully!', 'success')
        return redirect(url_for('exercise'))
    return render_template('add_exercise.html')

def populate_db():
    if Exercise.query.first() is None:
        csv_path = 'data/exercises.csv'
        exercises_data = pd.read_csv(csv_path)
        for index, row in exercises_data.iterrows():
            new_exercise = Exercise(
                name=row['Exercise'],
                body_part=row['Body Part'],
                type=row['Type'],
                sets=row['Sets'],
                reps=row['Reps (x)'],
                hold=row['Hold (s)'],
                total_time=row['Total Time (s)'],
                equipment=row['Equipment'],
                state=row['State'],
                level=row['Level'],
                space=row['Space'],
                directions=row['Directions'],
                added_by=row['Added by (us or user)']
            )
            db.session.add(new_exercise)
        db.session.commit()

populate_db()

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)