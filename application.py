import os
import re
from flask_jsglue import JSGlue
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from cs50 import SQL
from helpers import *
import threading

#in order to send text messages using this website you need a Twilio account. Store your Twilio SID, sender phone #, and AUTH token in a file called
#passwords.py via the naming convention below.
from passwords import TWILIO_SID, TWILIO_AUTH_TOKEN, SENDER_PHONE

# configure application
app = Flask(__name__)
JSGlue(app)

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Taken from previous PSETs to ensure responses aren't cached, allowing for easy debugging.
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response




# configure CS50 Library to use SQLite database
db = SQL("sqlite:///notify.db")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    #the index will be the home page. It will show user and notification data and provide links to manage users and notification templates
    #update


    # if user submits a JSON file
    if request.method == "POST":

        json_input = import_data()
        #template ID is 37 (from JSON file)
        template_id = json_input[0]["value"]
        template = db.execute("SELECT * FROM templates WHERE id=:id", id=template_id)
        delay_seconds = template[0]["delay_seconds"]
        message_text = template[0]["message_text"]

        #recipient user hardcoded to 1. In the future this data would come from the JSON and match with the app database (a copy of Epic's provider records)
        user_id = 1
        recipient_number = db.execute("SELECT phone_num FROM users WHERE id = :id", id=user_id)
        recipient_number = recipient_number[0]["phone_num"]

        message_id = db.execute("INSERT INTO 'notifications' (recipient_user_id, message_text, delay_seconds) VALUES(:recipient_user_id, :message_text, :delay_seconds)", recipient_user_id=user_id, message_text=message_text, delay_seconds=delay_seconds)
        set_notification_timer(delay_seconds, recipient_number, message_text, message_id)

        rows = db.execute("SELECT * FROM notifications JOIN users on notifications.recipient_user_id=users.id WHERE status=1")
        return render_template("active_notifications.html", rows=rows)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("index.html")

@app.route("/templates", methods=["GET", "POST"])
@login_required
@admin_required
def notification_templates():

    templates = db.execute("SELECT * FROM templates")

    if request.method == "POST":

        return render_template("templates.html")

    else:
        return render_template("templates.html", templates=templates)

@app.route("/new_template", methods=["GET", "POST"])
@login_required
@admin_required
def new_template():

    templates = db.execute("SELECT * FROM templates")

    if request.method == "POST":

        message_id = db.execute("INSERT INTO 'templates' (name, description, message_text, delay_seconds) VALUES(:name, :description, :message_text, :delay_seconds)", name=request.form["name"], description=request.form["description"], message_text=request.form["message_text"], delay_seconds=request.form["delay_seconds"])

        return render_template("templates.html")

    else:
        return render_template("new_template.html", templates=templates)


@app.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():

    rows = db.execute("SELECT * FROM users")
    return render_template("users.html", rows=rows)

@app.route("/active_notifications")
@login_required
@admin_required
def active_notifications():
    rows = db.execute("SELECT * FROM notifications JOIN users on notifications.recipient_user_id=users.id WHERE status=1")
    return render_template("active_notifications.html", rows=rows)

@app.route("/send_notification", methods=["GET", "POST"])
@login_required
@admin_required
def send_notification():


    if request.method == "POST":
        template_id = request.form["template_id"]
        if not template_id:
            delay_seconds = request.form["delay_seconds"]
            message_text = request.form["message_text"]

        else:
            template = db.execute("SELECT * FROM templates WHERE id=:id", id=template_id)
            delay_seconds = template[0]["delay_seconds"]
            message_text = template[0]["message_text"]

        user_id = request.form["recipient_user_id"]
        recipient_number = db.execute("SELECT phone_num FROM users WHERE id = :id", id=user_id)
        recipient_number = recipient_number[0]["phone_num"]

        message_id = db.execute("INSERT INTO 'notifications' (recipient_user_id, message_text, delay_seconds) VALUES(:recipient_user_id, :message_text, :delay_seconds)", recipient_user_id=request.form["recipient_user_id"], message_text=message_text, delay_seconds=delay_seconds)
        set_notification_timer(delay_seconds, recipient_number, message_text, message_id)
        return active_notifications()

    else:
        return render_template("send_notification.html")

@app.route("/history")
@login_required
@admin_required
def history():

    rows = db.execute("SELECT * FROM notifications JOIN users on notifications.recipient_user_id=users.id WHERE status=2")
    return render_template("history.html", rows=rows)

@app.route("/access_denied", methods=["GET", "POST"])
@login_required
def access_denied():

    ####update
    return render_template("access_denied.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    #Allow users to register for access to the site

    #for POST actions check registration data and register user if valid
    if request.method == "POST":

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        #if username doesnt exist
        if not rows:

            #create hash of password
            hashed_pw = pwd_context.hash(request.form.get("password"))


            #store data
            db.execute("INSERT INTO users (first_name, last_name, username, hash, phone_num, is_admin) VALUES(:first_name, :last_name, :username, :hashed_pw, :phone_num, :is_admin)", first_name=request.form["first_name"], last_name=request.form["last_name"], username=request.form["username"], hashed_pw = hashed_pw, phone_num = request.form["phone"], is_admin = request.form["is_admin"])

            # query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form["username"])

            # redirect user to home page
            return redirect(url_for("login"))

        #if username exists
        else:
            return render_template("login.html")

    #show registration screen for GET actions
    else:
        return render_template("register.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Log user out."""

    #set user's status to offline
    db.execute("UPDATE users SET active_status = 2 WHERE id = :id", id=session["user_id"])

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    #log the user in
    #update

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html")

        # ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return render_template("login.html")

        # check that user is not deactivated
        if rows[0]["active_status"] == 3:
            return render_template("login.html")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        #set user's status to online
        db.execute("UPDATE users SET active_status = 1 WHERE id = :id", id=session["user_id"])

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

#def receive_notification():
    #when a notification is received by the application this should store it to the database

def set_notification_timer(h, to_number, message_text, message_id):
    #when a notification is triggered for sending this should send it to appropriate user after h seconds
    h = int(h)
    try:
        Timer(h, send_notification, [to_number, message_text, message_id]).start()
    except:
        #this doesnt work yet
        print("time delay too large.")
        db.execute("UPDATE notifications SET status = 3 WHERE id = :message_id", message_id=message_id)



def send_notification(*args):
    #push the notification out to Twilio to send as a text
    # Account SID from twilio
    account_sid = TWILIO_SID
    # Auth Token from twilio.com (not set up for PRD)
    auth_token  = TWILIO_AUTH_TOKEN
    if not auth_token:
        raise RuntimeError("auth_token not set")

    client = Client(account_sid, auth_token)
    try:
        message = client.messages.create(
            to=args[0],
            from_=SENDER_PHONE,
            body=args[1])

        db.execute("UPDATE notifications SET status = 2 WHERE id = :message_id", message_id=args[2])
    except:
        print ("Twilio encountered an error in sending the message")
        db.execute("UPDATE notifications SET status = 3 WHERE id = :message_id", message_id=args[2])

def import_data():
    input_file = request.form.get("json_input")
    json_input = load_file(input_file)

    return json_input
