from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from datetime import datetime
import sys

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://timeboxing_user:Ali011111@localhost/timeboxing_db'

db = SQLAlchemy()
db.init_app(app)

class TimeboxingEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    top_priorities = db.Column(db.String(500))
    brain_dump = db.Column(db.Text)
    schedule = db.Column(db.JSON)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        top_priorities = request.form['top_priorities']
        brain_dump = request.form['brain_dump']
        schedule = {f"{h:02d}:{m:02d}": request.form.get(f"{h:02d}:{m:02d}", "") 
                    for h in range(5, 24) for m in (0, 30)}
        
        entry = TimeboxingEntry.query.filter_by(date=date).first()
        if entry:
            entry.top_priorities = top_priorities
            entry.brain_dump = brain_dump
            entry.schedule = schedule
        else:
            new_entry = TimeboxingEntry(date=date, top_priorities=top_priorities, 
                                        brain_dump=brain_dump, schedule=schedule)
            db.session.add(new_entry)
        
        db.session.commit()
        return redirect(url_for('index'))

    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    entry = TimeboxingEntry.query.filter_by(date=datetime.strptime(date, '%Y-%m-%d').date()).first()
    
    if entry:
        schedule = entry.schedule
    else:
        schedule = {f"{h:02d}:{m:02d}": "" for h in range(5, 24) for m in (0, 30)}

    return render_template('index.html', date=date, entry=entry, schedule=schedule)

@app.route('/history')
def view_history():
    entries = TimeboxingEntry.query.order_by(TimeboxingEntry.date.desc()).all()
    return render_template('view_history.html', entries=entries)

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully.")
        except OperationalError as e:
            print(f"Error connecting to the database: {e}")
            print("Please check your database credentials and permissions.")
            sys.exit(1)
    app.run(debug=True)