from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from collections import defaultdict
import io, csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    status = db.Column(db.String(50))
    score = db.Column(db.Integer)
    next_followup = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/dashboard')
def dashboard():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    status_counts = defaultdict(int)
    for lead in leads:
        status_counts[lead.status] += 1

    upcoming_followups = Lead.query.filter(
        Lead.next_followup >= datetime.utcnow().date(),
        Lead.next_followup <= datetime.utcnow().date() + timedelta(days=7)
    ).order_by(Lead.next_followup).all()

    recent_leads = Lead.query.order_by(Lead.updated_at.desc()).limit(5).all()

    return render_template("dashboard.html", 
        leads=leads, 
        status_counts=status_counts,
        total_leads=len(leads),
        upcoming_followups=upcoming_followups,
        recent_leads=recent_leads
    )

@app.route('/view')
def view_leads():
    selected_status = request.args.get('status')
    if selected_status:
        leads = Lead.query.filter_by(status=selected_status).order_by(Lead.updated_at.desc()).all()
    else:
        leads = Lead.query.order_by(Lead.updated_at.desc()).all()

    all_leads = Lead.query.all()
    status_counts = defaultdict(int)
    for lead in all_leads:
        status_counts[lead.status] += 1

    return render_template(
        "view_leads.html",
        leads=leads,
        status_counts=status_counts,
        selected_status=selected_status
    )

@app.route('/add', methods=['GET', 'POST'])
def add_lead():
    if request.method == 'POST':
        try:
            new_lead = Lead(
                name=request.form['name'],
                email=request.form['email'],
                status=request.form['status'].strip().capitalize(),  # fix
                score=int(request.form['score']),
                notes=request.form['notes'],
                next_followup=datetime.strptime(request.form['next_followup'], '%Y-%m-%d').date()
            )
            db.session.add(new_lead)
            db.session.commit()
            flash('Lead added successfully!')
            return redirect(url_for('view_leads'))
        except:
            flash('Error adding lead!')
            return redirect(url_for('add_lead'))
    return render_template("add_lead.html")

@app.route('/edit/<int:lead_id>', methods=['GET', 'POST'])
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if request.method == 'POST':
        try:
            lead.name = request.form['name']
            lead.email = request.form['email']
            lead.status = request.form['status'].strip().capitalize()  # fix
            lead.score = int(request.form['score'])
            lead.notes = request.form['notes']
            lead.next_followup = datetime.strptime(request.form['next_followup'], '%Y-%m-%d').date()
            db.session.commit()
            flash('Lead updated successfully!')
            return redirect(url_for('view_leads'))
        except:
            flash('Error updating lead!')
    return render_template("edit_lead.html", lead=lead)

@app.route('/delete/<int:lead_id>')
def delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted successfully!')
    return redirect(url_for('view_leads'))

@app.route('/export')
def export():
    leads = Lead.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Status', 'Score', 'Next Follow-Up', 'Notes', 'Created At', 'Updated At'])
    for lead in leads:
        writer.writerow([
            lead.id, lead.name, lead.email, lead.status, lead.score,
            lead.next_followup, lead.notes, lead.created_at, lead.updated_at
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='leads_export.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)
