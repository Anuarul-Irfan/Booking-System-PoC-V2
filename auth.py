# auth.py
from functools import wraps
from flask import session, redirect, url_for, flash
from firebase_admin import auth, firestore
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

# Define the admin_required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or session["user"].get("role") != "admin":
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# Example login route
from flask import Blueprint, request, render_template, redirect, url_for, session, flash
import requests
import json
import traceback
from firebase_config import db

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        # Firebase Web API Key
        api_key = os.getenv("FIREBASE_API_KEY")
        
        try:
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            auth_data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            auth_response = requests.post(auth_url, json=auth_data)
            auth_response.raise_for_status()
            
            user = auth.get_user_by_email(email)
            user_doc = db.collection('users').document(user.uid).get()  # Access Firestore

            if not user_doc.exists:
                user_data = {
                    'email': email,
                    'role': 'admin' if email == 'admin@example.com' else 'guard' if email == 'guard@example.com' else 'haulier',
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                db.collection('users').document(user.uid).set(user_data)  # Add user data to Firestore
            else:
                user_data = user_doc.to_dict()

            # Add debug print
            print("User role:", user_data.get('role'))

            session["user"] = {
                "uid": user.uid,
                "email": email,
                "role": user_data.get("role", "haulier")
            }

            # Add debug print
            print("Session data:", session["user"])

            if user_data.get("role") == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            elif user_data.get("role") == "guard":
                return redirect(url_for("guard.guard_dashboard"))
            else:
                return redirect(url_for("slots.haulier_dashboard"))

        except requests.exceptions.HTTPError as e:
            error_message = "Invalid email or password"
            if e.response is not None:
                error_data = e.response.json()
                if 'error' in error_data:
                    if error_data['error'].get('message') == 'EMAIL_NOT_FOUND':
                        error_message = "Email not found"
                    elif error_data['error'].get('message') == 'INVALID_PASSWORD':
                        error_message = "Invalid password"
            return render_template("login.html", error=error_message)

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()  # Clear all session data
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))
