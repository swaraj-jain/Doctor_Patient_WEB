from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_mail import Mail, Message
from random import randint
import requests
import time
import datetime
import pyrebase
import hashlib
import os
from PIL import Image
import numpy as np
import cv2

config = {
    "apiKey": "AIzaSyBztvVpB2d3Va3-jnDaySRdvbuiAv1wAbY",
    "authDomain": "docpat-39080.firebaseapp.com",
    "databaseURL": "https://docpat-39080-default-rtdb.firebaseio.com",
    "projectId": "docpat-39080",
    "storageBucket": "docpat-39080.appspot.com",
    "messagingSenderId": "904461611164",
    "appId": "1:904461611164:web:12e33fffd151d84bb67d59",
    "measurementId": "G-79EJQS44WG"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

app = Flask(__name__)
mail = Mail(app)
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = "swarajxxx69@gmail.com"
app.config['MAIL_PASSWORD'] = 'swarajfucks'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


DocForm = None
storage = firebase.storage()


def OTP_gen():
    return randint(100000, 1000000)


class DocRegisterForm(Form):
    docId = StringField('DocId', [
        validators.DataRequired(),
        validators.Length(min=1, max=50)
    ])
    name = StringField('Name', [validators.Length(min=1, max=50)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirmed', message='Passwords do not match')
    ])
    confirmed = PasswordField('Confirm Password')


class PatRegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirmed', message='Passwords do not match')
    ])
    confirmed = PasswordField('Confirm Password')


class DocLoginForm(Form):
    email = StringField('Email', [
        validators.DataRequired(),
        validators.Length(min=6, max=50)
    ])
    password = PasswordField('Password', [
        validators.DataRequired()
    ])


class PatLoginForm(Form):
    email = StringField('Email', [
        validators.DataRequired(),
        validators.Length(min=6, max=50)
    ])
    password = PasswordField('Password', [
        validators.DataRequired()
    ])


class OTPVerify(Form):
    otp = StringField('OTP', [
        validators.DataRequired(),
        validators.Length(min=6, max=6)
    ])


@app.route('/')
def index():
    form1 = PatLoginForm(request.form)
    form2 = DocLoginForm(request.form)
    return render_template('login.html', form1=form1, form2=form2)


################################################################################Patient Uploading his reports

@app.route('/pat_upload', methods=['GET', 'POST'])
def pat_upload():
    if request.method == 'POST':
        files = request.files.getlist("files")
        for i, file in enumerate(files):
            file = Image.open(file)
            file.save("tmp.jpeg", "JPEG")
            filepath = session['username'] + "/" + str(i) + str(time.time()) + ".jpeg"
            storage.child(filepath).put("tmp.jpeg")
            today = datetime.datetime.now()
            t_date = today.strftime("%d")+"/"+today.strftime("%m")+"/"+today.strftime("%Y")
            p_time = today.strftime("%H")+":"+today.strftime("%M")+":"+today.strftime("%S")
            url = storage.child(filepath).get_url(None)
            data = {
                "Url": url,
                "Pushed by": "Patient",
                "Date":t_date,
                "Time":p_time
            }
            db.child("Users/Patients/" + session['patient_id'] + '/Reports').push(data)
            os.remove("tmp.jpeg")

        print("Uploaded " + str(len(files)) + " files!")
        return redirect(url_for('pat_dashboard'))

    this_User =session['username']
    return render_template("pat_upload.html" , this_User = this_User)

#####################################################Doctor Uploading Report after taking acess from patient

@app.route('/doc_upload', methods=['GET', 'POST'])
def doc_upload():
    if request.method == 'POST':
        file = request.files['file']
        file = Image.open(file)
        file.save("tmp.jpeg", "JPEG")
        filepath = session['username'] + "/" + str(time.time()) + ".jpeg"
        storage.child(filepath).put("tmp.jpeg")
        url = storage.child(filepath).get_url(None)
        today = datetime.datetime.now()
        t_date = today.strftime("%d")+"/"+today.strftime("%m")+"/"+today.strftime("%Y")
        p_time = today.strftime("%H")+":"+today.strftime("%M")+":"+today.strftime("%S")
        data = {
            "Url": url,
            "Pushed by": session["username"],
            "Date":t_date,
            "Time":p_time
        }
        p_email=db.child("Users/Patients/" + session['patient_id'] + '/email').get().val()
        data2 = {
            "Url": url,
            "Pushed to": p_email,
            "Date":t_date,
            "Time":p_time
        }
        ##print(p_email)
        db.child("Users/Patients/" + session['patient_id'] + '/Reports').push(data) ##patient_id for doctor
        db.child("Users/Doctors/"+session['doc_ses_id']+"/g_Reports").push(data2)
        os.remove("tmp.jpeg")
        print("Uploaded files!")
        session['patient_id'] = ""
        return redirect(url_for('doc_dashboard'))

    this_User =session['username']
    return render_template("pat_upload.html", this_User = this_User)


################################################################################################Register

@app.route('/register', methods=['GET', 'POST'])
def register():
    form1 = PatRegisterForm(request.form)
    form2 = DocRegisterForm(request.form)
    return render_template('register.html', form1=form1, form2=form2)


@app.route('/patRegister', methods=['GET', 'POST'])
def patRregister():
    form = PatRegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        # To check if the patient is already registered.
        email = form.email.data

        users = db.child("Users/Patients").get().val()
        for x in users:
            if users[x]['email'] == email:
                flash("An account with this email already exists", "danger")
                return redirect(url_for('register'))

        name = form.name.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()

        data = {
            "name": name,
            "email": email,
            "password": password,
            "Reports": ""
        }

        db.child("Users/Patients").push(data)

        flash('Patient, you are now registered and can log in', 'success')

        return redirect(url_for('login'))

    return redirect(url_for('register'))


@app.route('/docVerify', methods=['GET', 'POST'])
def docVerify():
    global DocForm
    form = DocRegisterForm(request.form)

    if form.validate():
        email = form.email.data
        users = db.child("Users/Doctors").get().val()

        for x in users:
            if users[x]['email'] == email:
                flash("An account with this email already exists", "danger")
                return redirect(url_for('register'))

        DocForm = form
        msg = Message('OTP', sender='swarajxxx69@gmail.com', recipients=[email])
        OTP = OTP_gen()
        msg.body = str("Your secret OTP is: " + str(OTP))
        mail.send(msg)

        db.child("OTPs2").push({
            "email": email,
            "OTP": OTP
        })

        return redirect(url_for('otpVerify'))

    return redirect(url_for('register'))


@app.route('/otpVerify', methods=['GET', 'POST'])
def otpVerify():
    global DocForm

    otp = (OTPVerify(request.form)).otp.data
    otp2 = ""  # otp stored in the db

    if len(otp):
        OTPs = db.child("OTPs2").get().val()
        for OTP in OTPs:
            if OTPs[OTP]['email'] == DocForm.email.data:
                otp2 = OTPs[OTP]["OTP"]
                break
        print(otp2, otp, otp2 == otp)

        if str(otp) == str(otp2):
            docId = DocForm.docId.data
            name = DocForm.name.data
            email = DocForm.email.data
            password = hashlib.sha256(str(DocForm.password.data).encode())
            password = password.hexdigest()
            adress={                                            
                    'city':"",                             
                    'state':"",                            
                    'country':"",                             
                    'pincode':""                       
                }                            
            data = {
                "DocId": docId,
                "name": name,
                "email": email,
                "password": password,
                "g_Reports": "",
                "adress":adress                          
            }

            db.child("Users/Doctors").push(data)

            flash('Doctor, you are now registered and can log in', 'success')

            return redirect(url_for('login'))
        else:
            flash('Wrong otp', 'danger')

    return render_template('otpVerify.html', form=OTPVerify(request.form))


############################################ Login

@app.route('/login')
def login():
    return redirect(url_for('index'))

############################################################################## Doctor Login

@app.route('/docLogin', methods=['POST'])
def docLogin():
    form = DocLoginForm(request.form)
    if form.validate():
        email = form.email.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()
        user_id = None
        users = db.child("Users/Doctors").get().val()
        user = None
        for x in users:
            if users[x]['email'] == email and users[x]['password'] == password:
                user = users[x]
                user_id = x
                print(user)
                break

        if user is None:
            app.logger.info("Udd gye tote")
            flash('Please check your credentials', 'danger')
            return redirect(url_for('login'))
        else:
            app.logger.info("Welcome")

            session['logged_in'] = True
            session['username'] = user['name']
            session['email'] = user['email']
            session['doc_ses_id'] = user_id
            flash('Welcome ' + user['name'] + '!', 'success')

            return redirect(url_for('doc_dashboard'))

    return render_template('login.html', form2=form, form1=form)


####################################################################### Patient Login

@app.route('/patLogin', methods=['POST'])
def patLogin():
    form = PatLoginForm(request.form)
    if form.validate():
        email = form.email.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()

        users = db.child("Users/Patients").get().val()
        user = None
        user_id = None
        for x in users:
            if users[x]['email'] == email and users[x]['password'] == password:
                user = users[x]
                user_id = x
                print(user)
                break

        if user is None:
            app.logger.info("Udd gye tote")
            flash('Please check your credentials', 'danger')
            return redirect(url_for('login'))
        else:
            app.logger.info("Welcome")

            session['logged_in'] = True
            session['username'] = user['name']
            session['email'] = user['email']
            session['patient_id'] = user_id
            flash('Welcome ' + user['name'] + '!', 'success')

            return redirect(url_for('pat_dashboard'))

    return render_template('login.html', form1=form, form2=form)


###################################################################################################

# Check if the user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap



@app.route('/PatAccessDocOTP', methods=['POST'])
def PatAccessDocOTP():
    OTP = OTP_gen()
    db.child("OTPs").push({
        "patient_id": session['patient_id'],
        "OTP": OTP
    })
    this_User =session['username']
    return render_template('pat_dashboard.html', OTP=OTP , this_User = this_User)


@app.route('/Delete_OTP')
def Delete_OTP():
    time.sleep(10)

    if len(session['email']):    # yeh isiliye ki agar bich me user logout kar gya toh
        this_OTP="Your OTP is Expired"
        OTPs = db.child("OTPs").get().val()
        for OTP in OTPs:
            if OTPs[OTP]['patient_id'] == session['patient_id']:
                db.child("OTPs/"+OTP).remove()
    this_User =session['username']
    return render_template('pat_dashboard.html', OTP=this_OTP , this_User = this_User)

###########################################################################################

@app.route('/pat_dashboard')
@is_logged_in
def pat_dashboard():
    this_User =session['username']
    return render_template('pat_dashboard.html' , this_User = this_User)


###############################################################################################  Doctor part

@app.route('/doc_dashboard')
@is_logged_in
def doc_dashboard():
    this_User =session['username']
    return render_template('doc_dashboard.html', this_User = this_User)


################################################################## 


@app.route('/DocAccPatOTPVerify', methods=['POST'])
@is_logged_in
def DocAccPatOTPVerify():
    data = request.form
    Doc_OTP = data['OTP']

    #print(Doc_OTP)

    OTPs = db.child("OTPs").get().val()
    for x in OTPs:
        if str(OTPs[x]['OTP']) == str(Doc_OTP):
            pat_info = db.child("Users/Patients/" + OTPs[x]['patient_id']).get().val()
            session['patient_id'] = OTPs[x]['patient_id']
            this_User =session['username']
            return render_template('pds.html', pinfo=pat_info , this_User = this_User)

    flash('No Patient Found,Try Again', 'danger')
    return redirect(url_for('doc_dashboard'))

########################################################################################## Doctor complete

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for("login"))

#################################################################

@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')


#############################################################################Login Patient_oldreport

@app.route('/my_old_report')
@is_logged_in
def my_old_report():
    this_User =session['username']
    print("hiiii" + this_User)
    pinfo = db.child("Users/Patients/"+session['patient_id'] ).get().val()
    return render_template('my_old_report.html',pinfo = pinfo,this_User=this_User)

###############################################################################Login Doctor given Old Reports

@app.route('/my_given_oldreport')
@is_logged_in
def my_given_oldreport():
    p_data = db.child("Users/Doctors/"+session['doc_ses_id']+"/g_Reports").get().val()
    D_info = session
    print(D_info)
    this_User =session['username']
    return render_template('my_given_oldreport.html' , g_reports = p_data , D_info = D_info ,this_User = this_User)

######################################################################################################

######################################################################################################

@app.route('/my_profile')
@is_logged_in
def my_profile():
    d_data = db.child("Users/Doctors/"+session['doc_ses_id']).get().val()
    this_User =session['username']
    return render_template('my_profile.html', doctor = d_data ,this_User=this_User)

@app.route('/Update_my_profile' , methods=['POST'])
@is_logged_in
def Update_my_profile():
    f_data = request.form
    adress={
        'city':f_data['city'],
        'state':f_data['state'],
        'country':f_data['country'],
        'pincode':f_data['city_pin']
    }
    print(adress)

    db.child("Users/Doctors/"+session['doc_ses_id']+'/adress').update(adress)
    d_data = db.child("Users/Doctors/"+session['doc_ses_id']).get().val()
    print(d_data)
    flash('Profile had Been Update', 'success')
    return redirect(url_for('my_profile'))


#######################################################################################################

if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
