# user_management.py
from firebase_admin import auth, firestore

# Create user function
def create_user(email, password, role, db):  # Pass db as an argument to avoid circular import
    try:
        user = auth.create_user(
            email=email,
            password=password
        )
        # Store additional user data in Firestore
        users_ref = db.collection('users')
        users_ref.document(user.uid).set({
            'email': email,
            'role': role,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return user
    except Exception as e:
        raise Exception(f"Error creating user: {str(e)}")

# Function to get user data
def get_user(uid, db):  # Pass db as an argument to avoid circular import
    try:
        users_ref = db.collection('users')
        return users_ref.document(uid).get()
    except Exception as e:
        raise Exception(f"Error getting user: {str(e)}")
