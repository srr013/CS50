import csv
import urllib.request
from threading import Timer
from twilio.rest import Client
import json

from flask import redirect, render_template, request, session, url_for
from functools import wraps

#taken from PSET7 to require login at certain pages
def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def login_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return login_function

def apology():
    pass

def admin_required(f):
    @wraps(f)
    def admin_function(*args, **kwargs):
        if session.get("is_admin") is "off":
            return redirect(url_for("access_denied", next=request.url))
        return f(*args, **kwargs)
    return admin_function

def load_file(file):
    input_file = json.load(open(file))
    return_data = {}

    if input_file["resourceType"] == "Bundle":
        return_data["resourceType"] = "Bundle"
        return_data["value"] = input_file["entry"][0]["resource"]["valueQuantity"]["value"]
        return_data["unit"] = input_file["entry"][0]["resource"]["valueQuantity"]["unit"]

    return [return_data]
