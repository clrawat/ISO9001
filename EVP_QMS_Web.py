from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
import sqlite3, hashlib, csv, io, os
from datetime import date, datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('EVP_SECRET_KEY','change-this-secret-before-production')
DB='EVP_QMS_WEB.db'

FORMS=[
('F-01','Master Document List','7.5'),('F-02','Master Record List','7.5'),('F-03','Context & Interested Parties Register','4.1 / 4.2'),
('F-04','Risk & Opportunity Register','6.1'),('F-05','Quality Objectives & KPI Sheet','6.2'),('F-06','Training & Competence Record','7.2'),
('F-07','Enquiry / Quotation Review','8.2'),('F-08','Contract / Order Review','8.2'),('F-09','Design Review Record','8.3.4'),
('F-10','Design Verification / Validation Record','8.3.4'),('F-11','Supplier Evaluation & Re-evaluation','8.4'),('F-12','Purchase Order Review','8.4'),
('F-13','Incoming Inspection Report','8.4 / 8.6'),('F-14','Material Traceability Record','8.5.2'),('F-15','In-Process Inspection Report','8.5 / 8.6'),
('F-16','Final Inspection & Test Report','8.6'),('F-17','Product Release Note','8.6'),('F-18','Calibration Register','7.1.5'),
('F-19','Calibration / Verification Record','7.1.5'),('F-20','Preventive Maintenance Record','7.1.3'),('F-21','Job Card / Route Card','8.5'),
('F-22','Welding Inspection Report','8.5'),('F-23','Electrical Test Record','8.5 / 8.6'),('F-24','Hydraulic Pressure Test Record','8.5 / 8.6'),
('F-25','Functional Test Record','8.5 / 8.6'),('F-26','NCR Report','8.7'),('F-27','Rework / Repair Record','8.7'),
('F-28','Concession / Deviation Approval','8.7'),('F-29','Customer Complaint Register','9.1.2 / 10.2'),('F-30','CAPA Record','10.2'),
('F-31','Internal Audit Programme','9.2'),('F-32','Internal Audit Checklist','9.2'),('F-33','Internal Audit Report','9.2'),
('F-34','Management Review Agenda / Minutes','9.3'),('F-35','Improvement Action Register','10.3'),('F-36','Supplier Performance Scorecard','8.4'),
('F-37','Equipment Register','7.1.3'),('F-38','Product Serial Number Register','8.5.2')]

JCS=[('JC-01','Material Receipt, Identification & Cutting'),('JC-02','Machining / Fabrication'),('JC-03','Platen / Heater Element Manufacturing'),
('JC-04','Welding & Fabrication Inspection'),('JC-05','Electrical Assembly & Wiring'),('JC-06','Hydraulic Assembly'),('JC-07','Mechanical Assembly'),
('JC-08','In-Process Inspection'),('JC-09','Heat Test / Temperature Uniformity Test'),('JC-10','Electrical Safety Test'),
('JC-11','Hydraulic Pressure Test'),('JC-12','Functional / Final Test'),('JC-13','Final Inspection & Product Release'),('JC-14','Packing & Dispatch')]

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def h(s): return hashlib.sha256(s.encode()).hexdigest()

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,full_name TEXT,role TEXT,department TEXT,active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,job_no TEXT UNIQUE,customer TEXT,product TEXT,model TEXT,po_no TEXT,order_date TEXT,due_date TEXT,status TEXT DEFAULT 'OPEN',drawing_no TEXT,serial_no TEXT,specification TEXT,remarks TEXT,created_by TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY,form_no TEXT,form_name TEXT,record_no TEXT UNIQUE,job_no TEXT,record_date TEXT,department TEXT,owner TEXT,status TEXT,details TEXT,result TEXT,approved_by TEXT,revision TEXT,created_by TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS jobcards(id INTEGER PRIMARY KEY,job_no TEXT,card_no TEXT,operation TEXT,operator TEXT,inspector TEXT,status TEXT,result TEXT,remarks TEXT,updated_by TEXT,updated_at TEXT);
    CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY,action_type TEXT,ref_no TEXT,job_no TEXT,description TEXT,root_cause TEXT,corrective_action TEXT,owner TEXT,target_date TEXT,status TEXT,created_by TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user TEXT,action TEXT,object_type TEXT,object_ref TEXT,ts TEXT);
    ''')
    if not c.execute('SELECT 1 FROM users').fetchone():
        c.execute('INSERT INTO users(username,password,full_name,role,department) VALUES(?,?,?,?,?)',('admin',h('admin123'),'EVP Administrator','ADMIN','Management'))
    c.commit(); c.close()

def audit(action,obj,ref):
    c=db(); c.execute('INSERT INTO audit(user,action,object_type,object_ref,ts) VALUES(?,?,?,?,?)',(session.get('user','?'),action,obj,ref,datetime.now().isoformat(timespec='seconds'))); c.commit(); c.close()

def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if 'user' not in session:return redirect(url_for('login'))
        return f(*a,**k)
    return w

BASE='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EVP QMS</title>
<style>body{margin:0;font-family:Arial,sans-serif;background:#f4f6f8;color:#17212b}.top{background:#123c69;color:white;padding:16px 24px}.top b{font-size:21px}.nav{background:#fff;padding:10px 24px;border-bottom:1px solid #ddd}.nav a{margin-right:18px;text-decoration:none;color:#123c69;font-weight:600}.wrap{padding:22px;max-width:1450px;margin:auto}.card{background:white;border-radius:10px;padding:18px;margin-bottom:16px;box-shadow:0 1px 4px #ccd}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.metric{font-size:30px;font-weight:bold;color:#123c69}.btn{background:#123c69;color:#fff;border:0;padding:9px 13px;border-radius:6px;text-decoration:none;cursor:pointer}.btn2{background:#e8eef5;color:#123c69;padding:9px 13px;border-radius:6px;text-decoration:none}table{border-collapse:collapse;width:100%;background:white}th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left}th{background:#e8eef5}input,select,textarea{width:100%;box-sizing:border-box;padding:8px;margin:4px 0 10px;border:1px solid #bbb;border-radius:5px}label{font-weight:bold}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}.flash{background:#fff3cd;padding:10px;border-radius:5px;margin-bottom:12px}@media(max-width:700px){.two{grid-template-columns:1fr}.nav a{display:inline-block;margin-bottom:8px}}</style></head><body>
<div class="top"><b>EVP CONVEYOR PRODUCTS PVT. LTD.</b><br><small>ISO 9001:2015 Quality Management System</small></div>
{% if session.user %}<div class="nav"><a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('jobs')}}">Jobs</a><a href="{{url_for('forms')}}">F-01–F-38</a><a href="{{url_for('jobcards')}}">Job Cards</a><a href="{{url_for('actions')}}">NCR/CAPA</a>{% if session.role=='ADMIN' %}<a href="{{url_for('users')}}">Users</a><a href="{{url_for('auditlog')}}">Audit Trail</a>{% endif %}<a href="{{url_for('logout')}}">Logout ({{session.user}})</a></div>{% endif %}
<div class="wrap">{% with m=get_flashed_messages() %}{% for x in m %}<div class="flash">{{x}}</div>{% endfor %}{% endwith %}{{body|safe}}</div></body></html>'''

def page(body,**kw):return render_template_string(BASE,body=render_template_string(body,**kw))

@app.route('/',methods=['GET','POST'])
def login():
    if request.method=='POST':
        c=db(); u=c.execute('SELECT * FROM users WHERE username=? AND password=? AND active=1',(request.form['username'],h(request.form['password']))).fetchone(); c.close()
        if u: session.update(user=u['username'],name=u['full_name'],role=u['role'],department=u['department']); return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return page('''<div class="card" style="max-width:420px;margin:50px auto"><h2>EVP QMS Login</h2><form method=post><label>Username</label><input name=username required><label>Password</label><input name=password type=password required><button class=btn>Login</button></form><p><small>Initial administrator: admin / admin123 — change it after first login.</small></p></div>''')

@app.route('/logout')
def logout():session.clear();return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    c=db(); counts={'jobs':c.execute("SELECT count(*) n FROM jobs WHERE status!='CLOSED'").fetchone()['n'],'records':c.execute("SELECT count(*) n FROM records WHERE status!='CLOSED'").fetchone()['n'],'actions':c.execute("SELECT count(*) n FROM actions WHERE status!='CLOSED'").fetchone()['n'],'cards':c.execute("SELECT count(*) n FROM jobcards WHERE status!='COMPLETED'").fetchone()['n']}; c.close()
    return page('''<h2>Quality Dashboard</h2><div class=grid>{% for n,v in [('Open Jobs',x.jobs),('Open QMS Records',x.records),('Open NCR/CAPA',x.actions),('Pending Job Cards',x.cards)] %}<div class=card><div>{{n}}</div><div class=metric>{{v}}</div></div>{% endfor %}</div><div class=card><h3>EVP Controlled Process</h3><p>Enquiry → Order Review → Design → Procurement → Material Receipt → Manufacturing → Inspection & Testing → Product Release → Dispatch → Feedback / CAPA</p></div>''',x=counts)

@app.route('/jobs')
@login_required
def jobs():
    c=db(); r=c.execute('SELECT * FROM jobs ORDER BY id DESC').fetchall();c.close()
    return page('''<h2>Job Master</h2><p><a class=btn href="{{url_for('new_job')}}">+ New Job</a></p><table><tr><th>Job No</th><th>Customer</th><th>Product</th><th>PO</th><th>Due</th><th>Status</th></tr>{% for r in rows %}<tr><td>{{r.job_no}}</td><td>{{r.customer}}</td><td>{{r.product}}</td><td>{{r.po_no}}</td><td>{{r.due_date}}</td><td>{{r.status}}</td></tr>{% endfor %}</table>''',rows=r)

@app.route('/jobs/new',methods=['GET','POST'])
@login_required
def new_job():
    if request.method=='POST':
        c=db()
        try:c.execute('INSERT INTO jobs(job_no,customer,product,model,po_no,order_date,due_date,status,drawing_no,serial_no,specification,remarks,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',tuple(request.form.get(k,'') for k in ['job_no','customer','product','model','po_no','order_date','due_date','status','drawing_no','serial_no','specification','remarks'])+(session['user'],datetime.now().isoformat(timespec='seconds')));c.commit();audit('CREATE','JOB',request.form['job_no']);return redirect(url_for('jobs'))
        except sqlite3.IntegrityError:flash('Job number already exists.')
        finally:c.close()
    return page('''<h2>New Job</h2><form method=post class=card><div class=two>{% for k,l in fields %}<div><label>{{l}}</label>{% if k=='status' %}<select name=status><option>OPEN</option><option>DESIGN</option><option>PROCUREMENT</option><option>MANUFACTURING</option><option>TESTING</option><option>READY</option><option>DISPATCHED</option><option>CLOSED</option></select>{% else %}<input name={{k}} {% if k=='job_no' %}required{% endif %}></div>{% endfor %}</div><label>Specification</label><textarea name=specification></textarea><label>Remarks</label><textarea name=remarks></textarea><button class=btn>Save Job</button></form>''',fields=[('job_no','Job No'),('customer','Customer'),('product','Product'),('model','Model'),('po_no','PO No'),('order_date','Order Date'),('due_date','Due Date'),('status','Status'),('drawing_no','Drawing No'),('serial_no','Serial No')])

@app.route('/forms')
@login_required
def forms():
    c=db(); rec=c.execute('SELECT * FROM records ORDER BY id DESC LIMIT 100').fetchall();c.close()
    return page('''<h2>EVP ISO 9001:2015 Forms</h2><div class=card><table><tr><th>Form</th><th>Title</th><th>Clause</th><th></th></tr>{% for f in forms %}<tr><td>{{f[0]}}</td><td>{{f[1]}}</td><td>{{f[2]}}</td><td><a class=btn2 href="{{url_for('new_record',form_no=f[0])}}">Create Record</a></td></tr>{% endfor %}</table></div><h3>Recent Records</h3><table><tr><th>Record No</th><th>Form</th><th>Job</th><th>Date</th><th>Status</th></tr>{% for r in rec %}<tr><td>{{r.record_no}}</td><td>{{r.form_no}}</td><td>{{r.job_no}}</td><td>{{r.record_date}}</td><td>{{r.status}}</td></tr>{% endfor %}</table>''',forms=FORMS,rec=rec)

@app.route('/records/new/<form_no>',methods=['GET','POST'])
@login_required
def new_record(form_no):
    fd=next((x for x in FORMS if x[0]==form_no),None)
    if not fd:return 'Unknown form',404
    if request.method=='POST':
        c=db(); n=c.execute('SELECT count(*) n FROM records WHERE form_no=?',(form_no,)).fetchone()['n']+1; rn=request.form.get('record_no') or f'{form_no}-{date.today().year}-{n:04d}'
        c.execute('INSERT INTO records(form_no,form_name,record_no,job_no,record_date,department,owner,status,details,result,approved_by,revision,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(form_no,fd[1],rn,request.form['job_no'],request.form['record_date'],request.form['department'],request.form['owner'],request.form['status'],request.form['details'],request.form['result'],request.form['approved_by'],request.form['revision'],session['user'],datetime.now().isoformat(timespec='seconds')));c.commit();c.close();audit('CREATE','QMS RECORD',rn);return redirect(url_for('forms'))
    return page('''<h2>{{f[0]}} — {{f[1]}}</h2><form method=post class=card><div class=two><div><label>Record No (blank = automatic)</label><input name=record_no></div><div><label>Job No</label><input name=job_no></div><div><label>Date</label><input name=record_date value="{{today}}"></div><div><label>Department</label><input name=department value="{{session.department}}"></div><div><label>Owner</label><input name=owner value="{{session.name}}"></div><div><label>Status</label><select name=status><option>OPEN</option><option>IN REVIEW</option><option>APPROVED</option><option>CLOSED</option></select></div><div><label>Result</label><select name=result><option></option><option>PASS</option><option>FAIL</option><option>NA</option></select></div><div><label>Revision</label><input name=revision value=00></div><div><label>Approved By</label><input name=approved_by></div></div><label>Details / Evidence / Acceptance Criteria</label><textarea rows=10 name=details></textarea><button class=btn>Save Record</button></form>''',f=fd,today=date.today().isoformat())

@app.route('/jobcards')
@login_required
def jobcards():
    c=db();r=c.execute('SELECT * FROM jobcards ORDER BY id DESC').fetchall();c.close()
    return page('''<h2>Manufacturing Job / Route Cards</h2><p><a class=btn href="{{url_for('new_jobcard')}}">+ New Job Card</a></p><table><tr><th>Job</th><th>Card</th><th>Operation</th><th>Operator</th><th>Inspector</th><th>Status</th><th>Result</th></tr>{% for r in rows %}<tr><td>{{r.job_no}}</td><td>{{r.card_no}}</td><td>{{r.operation}}</td><td>{{r.operator}}</td><td>{{r.inspector}}</td><td>{{r.status}}</td><td>{{r.result}}</td></tr>{% endfor %}</table>''',rows=r)

@app.route('/jobcards/new',methods=['GET','POST'])
@login_required
def new_jobcard():
    if request.method=='POST':
        op=dict(JCS).get(request.form['card_no'],'')
        c=db();c.execute('INSERT INTO jobcards(job_no,card_no,operation,operator,inspector,status,result,remarks,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(request.form['job_no'],request.form['card_no'],op,request.form['operator'],request.form['inspector'],request.form['status'],request.form['result'],request.form['remarks'],session['user'],datetime.now().isoformat(timespec='seconds')));c.commit();c.close();audit('CREATE','JOB CARD',request.form['job_no']+' '+request.form['card_no']);return redirect(url_for('jobcards'))
    return page('''<h2>New Job Card</h2><form method=post class=card><label>Job No</label><input name=job_no required><label>Card</label><select name=card_no>{% for x in jcs %}<option value="{{x[0]}}">{{x[0]}} — {{x[1]}}</option>{% endfor %}</select><div class=two><div><label>Operator</label><input name=operator></div><div><label>Inspector</label><input name=inspector></div><div><label>Status</label><select name=status><option>PENDING</option><option>IN PROCESS</option><option>HOLD</option><option>COMPLETED</option><option>REJECTED</option></select></div><div><label>Result</label><select name=result><option></option><option>PASS</option><option>FAIL</option><option>NA</option></select></div></div><label>Remarks</label><textarea name=remarks></textarea><button class=btn>Save</button></form>''',jcs=JCS)

@app.route('/actions',methods=['GET','POST'])
@login_required
def actions():
    if request.method=='POST':
        c=db();c.execute('INSERT INTO actions(action_type,ref_no,job_no,description,root_cause,corrective_action,owner,target_date,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',tuple(request.form.get(k,'') for k in ['action_type','ref_no','job_no','description','root_cause','corrective_action','owner','target_date','status'])+(session['user'],datetime.now().isoformat(timespec='seconds')));c.commit();c.close();audit('CREATE','NCR/CAPA',request.form['ref_no']);return redirect(url_for('actions'))
    c=db();r=c.execute('SELECT * FROM actions ORDER BY id DESC').fetchall();c.close()
    return page('''<h2>NCR / CAPA / Improvement</h2><form method=post class=card><div class=two><div><label>Type</label><select name=action_type><option>NCR</option><option>CAPA</option><option>COMPLAINT</option><option>IMPROVEMENT</option></select></div><div><label>Reference No</label><input name=ref_no required></div><div><label>Job No</label><input name=job_no></div><div><label>Owner</label><input name=owner></div><div><label>Target Date</label><input name=target_date></div><div><label>Status</label><select name=status><option>OPEN</option><option>INVESTIGATION</option><option>ACTION</option><option>VERIFY</option><option>CLOSED</option></select></div></div><label>Description</label><textarea name=description></textarea><label>Root Cause</label><textarea name=root_cause></textarea><label>Corrective Action</label><textarea name=corrective_action></textarea><button class=btn>Save</button></form><table><tr><th>Type</th><th>Ref</th><th>Job</th><th>Description</th><th>Owner</th><th>Target</th><th>Status</th></tr>{% for r in rows %}<tr><td>{{r.action_type}}</td><td>{{r.ref_no}}</td><td>{{r.job_no}}</td><td>{{r.description}}</td><td>{{r.owner}}</td><td>{{r.target_date}}</td><td>{{r.status}}</td></tr>{% endfor %}</table>''',rows=r)

@app.route('/users',methods=['GET','POST'])
@login_required
def users():
    if session['role']!='ADMIN':return 'Forbidden',403
    if request.method=='POST':
        c=db()
        try:c.execute('INSERT INTO users(username,password,full_name,role,department) VALUES(?,?,?,?,?)',(request.form['username'],h(request.form['password']),request.form['full_name'],request.form['role'],request.form['department']));c.commit();flash('User created.')
        except sqlite3.IntegrityError:flash('Username already exists.')
        c.close()
    c=db();r=c.execute('SELECT id,username,full_name,role,department,active FROM users').fetchall();c.close()
    return page('''<h2>User Management</h2><form method=post class=card><div class=two><div><label>Username</label><input name=username required></div><div><label>Password</label><input type=password name=password required></div><div><label>Full Name</label><input name=full_name required></div><div><label>Role</label><select name=role><option>ADMIN</option><option>QUALITY</option><option>DESIGN</option><option>PURCHASE</option><option>PRODUCTION</option><option>INSPECTION</option><option>VIEWER</option></select></div><div><label>Department</label><input name=department></div></div><button class=btn>Create User</button></form><table><tr><th>Username</th><th>Name</th><th>Role</th><th>Department</th><th>Active</th></tr>{% for r in rows %}<tr><td>{{r.username}}</td><td>{{r.full_name}}</td><td>{{r.role}}</td><td>{{r.department}}</td><td>{{r.active}}</td></tr>{% endfor %}</table>''',rows=r)

@app.route('/audit')
@login_required
def auditlog():
    if session['role']!='ADMIN':return 'Forbidden',403
    c=db();r=c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 500').fetchall();c.close()
    return page('''<h2>Audit Trail</h2><table><tr><th>Time</th><th>User</th><th>Action</th><th>Object</th><th>Reference</th></tr>{% for r in rows %}<tr><td>{{r.ts}}</td><td>{{r.user}}</td><td>{{r.action}}</td><td>{{r.object_type}}</td><td>{{r.object_ref}}</td></tr>{% endfor %}</table>''',rows=r)

if __name__=='__main__':
    init_db()
    print('EVP QMS Web: http://127.0.0.1:8000')
    print('LAN access: http://YOUR-MAC-IP:8000')
    app.run(host='0.0.0.0',port=8000,debug=False)
