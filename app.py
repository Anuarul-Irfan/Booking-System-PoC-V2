# app.py
from flask import Flask
from flask_cors import CORS
import os
from auth import auth_bp
from admin import admin_bp
from slots import slots_bp
from guard import guard_bp
from firebase_config import initialize_firebase
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app)

# Set the session lifetime to 24 hours
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Initialize Firebase
initialize_firebase()

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(slots_bp)
app.register_blueprint(guard_bp, url_prefix='/guard')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
