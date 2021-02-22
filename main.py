# Developed by @proh_gram_er

from flask import Flask, request, session, redirect, url_for, render_template
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import timedelta
import firebase_admin
import datetime
import xlrd
import time


''' google firebase firestore connectivity '''

cred = credentials.Certificate('service\key.json')
firebase_admin.initialize_app(cred)
db = firestore.client()


''' web application attributes '''

app = Flask(__name__)
app.secret_key = 'CODECOL'
app.permanent_session_lifetime = timedelta(days=7)


''' check if id exists in firestore'''


def exists(id):
    try:
        user = db.collection(
            'administrator' if id[:5] == '@hod.' else 'faculties' if id[:5] == '@fac.' else 'students').document(id).get()
        if user.exists:
            session['subject' if id[:5] == '@fac.' else 'roll_no'] = user.to_dict().get(
                'subject' if id[:5] == '@fac.' else 'roll_no')
            session['id'] = id
            session.permanent = True
            return True
        return False
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' send relevant identifier'''


def get_identifier(id):
    return 'hod' if id[:5] == '@hod.' else "faculty" if id[:5] == '@fac.' else 'student'


''' get sessions details '''


def get_lectures(name=None):
    try:
        date = datetime.datetime.now()
        now = datetime.datetime.now()
        day = now.strftime("%A")
        lecs = {}
        todays_lecs = db.collection('sessions').document(day).collections()
        for lectures in todays_lecs:
            for lecture in lectures.stream():
                if not name:
                    lecs[lecture.id] = lecture.to_dict()
                elif name == lecture.id:
                    return get_posted_link(lecture.to_dict(), date)
        if lecs:
            return get_links(lecs, date)
        return None
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' check for new link '''


def get_posted_link(lecture, date):
    try:
        link = db.collection('links').document(lecture['subject']).get()
        if link.exists:
            if link.to_dict().get('link').partition('.')[0] == f'{date.month}-{date.day}':
                lecture['link'] = link.to_dict().get('link').partition('.')[2]
        return lecture
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' check for new links '''


def get_links(lectures, date):
    try:
        links = db.collection('links').get()
        if (links):
            for link in links:
                for faculty, lecture in lectures.items():
                    if link.id == lecture.get('subject'):
                        if link.to_dict().get('link').partition('.')[0] == f'{date.month}-{date.day}':
                            lectures[faculty]['link'] = link.to_dict().get(
                                'link').partition('.')[2]
            return lectures
        return None
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' index page route '''


@ app.route('/', methods=['POST', 'GET'])
def index():
    try:
        error = None
        if request.method == 'POST':
            id = str(request.form.get('id')).lower()
            if id.find('@') != 0 or id.find('.') != 4:
                error = 'invalid id'
            else:
                if exists(id):
                    return redirect(url_for(get_identifier(id)))
                else:
                    error = 'not found'
        else:
            if 'id' in session:
                id = session['id']
                return redirect(url_for(get_identifier(id)))
        return render_template('index.html', error=error)
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' Module: HOD '''


@ app.route('/hod', methods=['GET'])
def hod():
    try:
        if 'id' in session:
            id = session['id']
            user = db.collection('administrator').document(id).get()
            announcements = db.collection('announcements').get()
            events = db.collection('events').get()
            return render_template('hod.html', first_name=user.to_dict().get('first_name').title(), last_name=user.to_dict().get('last_name').title(), announcements=announcements, events=events)
        else:
            return render_template('index.html')
    except Exception as exc:
        return render_template('exception.html', exception=exc)


@ app.route('/add_faculty', methods=['POST', 'GET'])
def add_faculty():
    error = None
    success = None
    identifier = '@fac.'
    if request.method == 'POST':
        try:
            data = dict(request.form)
            id = str(identifier+data.get('first_name') +
                     data.get('birth_date').replace('-', '')).lower()
            user = db.collection('faculties').document(id).get()
            if not user.exists:
                db.collection('faculties').document(id).set({
                    'first_name': data.get('first_name').lower(),
                    'last_name': data.get('last_name').lower(),
                    'subject': data.get('subject').lower(),
                    'birth_date': data.get('birth_date'),
                    'contact_no': f"+91 {data.get('contact_no')}",
                    'address': data.get('address').lower()
                })
                success = 'successfully added'
            else:
                error = 'already exists'
        except Exception as exc:
            return render_template('exception.html', exception=exc)
    return render_template('table.html', identifier=identifier, error=error, success=success)


@ app.route('/assign_session', methods=['POST', 'GET'])
def assign_session():
    error = None
    success = None
    if request.method == 'POST':
        try:
            data = dict(request.form)
            user = db.collection('faculties').where(
                'first_name', '==', data.get('name').lower()).get()
            if(user):
                db.collection('sessions').document(data.get('day')).collection(data.get('idx')).document(data.get('name').lower()).set({
                    'subject': data.get('subject').lower(),
                    'time': data.get('time').lower()
                }, merge=True)
                success = 'successfully assigned'
            else:
                error = 'not found'
        except Exception as exc:
            return render_template('exception.html', exception=exc)
    return render_template('assign.html', error=error, success=success)


@ app.route('/announcement', methods=['POST', 'GET'])
def announcement():
    if request.method == 'POST':
        try:
            data = dict(request.form)
            db.collection('announcements').add(data)
            return redirect(url_for('hod'))
        except Exception as exc:
            return render_template('exception.html', exception=exc)
    return render_template('anncmnt-evnt.html')


@ app.route('/event', methods=['POST', 'GET'])
def event():
    if request.method == 'POST':
        try:
            data = dict(request.form)
            db.collection('events').add(data)
            return redirect(url_for('hod'))
        except Exception as exc:
            return render_template('exception.html', exception=exc)
    return render_template('anncmnt-evnt.html')


''' Module: Faculties '''


@ app.route('/faculty', methods=['POST', 'GET'])
def faculty():
    error = None
    try:
        if 'id' in session:
            id = session['id']
            subject = session['subject']
            date = datetime.datetime.now()
            user = db.collection('faculties').document(id).get()
            lecture = get_lectures(user.to_dict().get('first_name').lower())
            announcements = db.collection('announcements').get()
            events = db.collection('events').get()
            if request.method == 'POST':
                if(lecture):
                    link = request.form.get('link')
                    db.collection('links').document(
                        lecture['subject']).set({
                            'subject': lecture['subject'],
                            'link': f"{date.month}-{date.day}.{link}"
                        })
                    lecture['link'] = link
                else:
                    error = "you don't have any session today"
            return render_template('faculty.html', first_name=user.to_dict().get('first_name').title(), last_name=user.to_dict().get('last_name').title(), subject=subject.title(), lecture=lecture, error=error, announcements=announcements, events=events)
        else:
            return render_template('index.html')
    except Exception as exc:
        return render_template('exception.html', exception=exc)


@ app.route('/add_student', methods=['POST', 'GET'])
def add_student():
    error = None
    success = None
    identifier = '@stu.'
    if request.method == 'POST':
        try:
            data = dict(request.form)
            id = str(identifier+data.get('first_name') +
                     data.get('birth_date').replace('-', '')).lower()
            user = db.collection('students').document(id).get()
            if not user.exists:
                db.collection('students').document(id).set({
                    'first_name': data.get('first_name').lower(),
                    'last_name': data.get('last_name').lower(),
                    'roll_no': data.get('roll_no'),
                    'birth_date': data.get('birth_date'),
                    'contact_no': f"+91 {data.get('contact_no')}",
                    'address': data.get('address').lower()
                })
                success = 'successfully added'
            else:
                error = 'already exists'
        except Exception as exc:
            return render_template('exception.html', exception=exc)
    return render_template('table.html', identifier=identifier, error=error, success=success)


@ app.route('/attendance', methods=['POST', 'GET'])
def attendance():
    pass


@ app.route('/result', methods=['POST', 'GET'])
def result():
    # result = {}
    error = None
    try:
        if request.method == 'POST':
            xlsx = request.form.get('file')
            if xlsx[-5:] == '.xlsx':
                workbook = xlrd.open_workbook(xlsx)
                sheet = workbook.sheet_by_index(0)
                if sheet.cell_value(0, 0).lower() == session['subject']:
                    if sheet.nrows > 3 and sheet.ncols == 3:
                        subject = sheet.cell_value(0, 0).lower()
                        data = {}
                        for row in range(3, sheet.nrows):
                            for col in range(sheet.ncols):
                                data[col] = sheet.cell_value(row, col)
                            db.collection('results').document(str(int(data[0]))).set(
                                {'name': data[1], subject.lower(): data[2]})
                        result = db.collection('results').get()
                        for res in result:
                            print(res.to_dict())
                        return render_template('result.html', result=result, error=error)
                    else:
                        error = 'invalid format'
                else:
                    error = 'invalid subject'
            else:
                error = 'only .xlsx supported'
        results = db.collection('results').get()
        result = {}
        for res in results:
            result[res.id] = res.to_dict()
        for res in result.values():
            print(res)
        return render_template('result.html', **result, error=error)
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' Module: Students '''


@ app.route('/student', methods=['POST', 'GET'])
def student():
    try:
        if 'id' in session:
            id = session['id']
            roll_no = session['roll_no']
            user = db.collection('students').document(id).get()
            lectures = get_lectures()
            announcements = db.collection('announcements').get()
            events = db.collection('events').get()
            return render_template('student.html', first_name=user.to_dict().get('first_name').title(), last_name=user.to_dict().get('last_name').title(), roll_no=roll_no, lectures=lectures, announcements=announcements, events=events)
        else:
            return render_template('index.html')
    except Exception as exc:
        return render_template('exception.html', exception=exc)


''' go back to previous route '''


@ app.route('/back')
def back():
    return redirect(url_for(get_identifier(session['id'])))


''' logout '''


@ app.route('/logout')
def logout():
    session.pop('id', None)
    session.pop('subject', None)
    session.pop('roll_no', None)
    return redirect(url_for('index'))


''' Execute web application '''


if __name__ == '__main__':
    app.run()

# if request.method == 'POST':
#     data = dict(request.form)
#     user = db.collection('admin').document(data.get('userid').lower()).get()
#     if user.exists:
#         return render_template('index.html')
#     return render_template('error.html')
