import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import traceback

# Initialize Firebase
def initialize_firebase():
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Get the absolute path to the service account key file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            key_path = os.path.join(current_dir, 'serviceAccountKey.json')
            
            if not os.path.exists(key_path):
                raise FileNotFoundError(f"serviceAccountKey.json not found at {key_path}")
            
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
        else:
            print("Firebase already initialized")
            
        # Get Firestore database instance
        return firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        raise

# Initialize Firestore database
try:
    db = initialize_firebase()
except Exception as e:
    print(f"Failed to initialize Firestore: {str(e)}")
    db = None

# Function to fetch all booked slots (those with 'bookedBy' not None)
def get_all_booked_slots():
    try:
        # Get all booked slots
        booked_slots = [
            doc.to_dict() | {'id': doc.id} 
            for doc in db.collection('slots')
            .where('bookedBy', '!=', None)
            .stream()
        ]
        
        # Filter out completed slots
        filtered_slots = [
            slot for slot in booked_slots
            if slot.get('status') != 'completed'
        ]
        
        return filtered_slots
    except Exception as e:
        print(f"Error fetching booked slots: {str(e)}")
        raise

# Function to create a new user
def create_user(email, password, role):
    try:
        # Create the user using Firebase Authentication
        user = auth.create_user(
            email=email,
            password=password
        )

        # Store additional user data in Firestore
        users_ref = db.collection('users')
        users_ref.document(user.uid).set({
            'email': email,
            'role': role,  # Store the role (e.g., admin, haulier, guard)
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return user
    except Exception as e:
        raise Exception(f"Error creating user: {str(e)}")

# Function to create attendance record
def create_attendance(slot_id):
    try:
        # Get the slot document
        slot_ref = db.collection('slots').document(slot_id)
        slot_doc = slot_ref.get()
        
        if not slot_doc.exists:
            raise ValueError("Slot not found")
            
        slot_data = slot_doc.to_dict()
        truck_plate = slot_data.get('truckPlate')
        
        if not truck_plate:
            raise ValueError("No vehicle plate found for this booking")
        
        # Create attendance record
        attendance_data = {
            'slotId': slot_id,
            'truckPlate': truck_plate,
            'timeIn': firestore.SERVER_TIMESTAMP,
            'timeOut': None,
            'status': 'in_terminal',
            'product': slot_data.get('product'),
            'bookedBy': slot_data.get('bookedBy'),
            'time': slot_data.get('time')
        }
        
        # Add attendance record
        attendance_ref = db.collection('attendance').add(attendance_data)
        
        # Update the slot status
        slot_ref.update({
            'status': 'checked_in',
            'attendanceId': attendance_ref[1].id
        })
        
        print(f"Successfully created attendance for vehicle {truck_plate}")
        return True
        
    except Exception as e:
        print(f"Error creating attendance: {str(e)}")
        raise

# Function to get all active check-ins (status "in_terminal")
def get_active_attendance():
    try:
        # Get all active attendance records
        attendance_records = [
            doc.to_dict() | {'id': doc.id} 
            for doc in db.collection('attendance')
            .where('status', '==', 'in_terminal')
            .stream()
        ]
        
        # Get corresponding slot data
        for record in attendance_records:
            if record.get('slotId'):
                slot_doc = db.collection('slots').document(record['slotId']).get()
                if slot_doc.exists:
                    slot_data = slot_doc.to_dict()
                    record['time'] = slot_data.get('time')
                    record['product'] = slot_data.get('product')
                    record['bookedBy'] = slot_data.get('bookedBy')
        
        return attendance_records
    except Exception as e:
        print(f"Error fetching active attendance: {str(e)}")
        raise

# Function to mark attendance as exited
def mark_as_exited(attendance_id):
    try:
        # Get the attendance record first
        attendance_ref = db.collection('attendance').document(attendance_id)
        attendance_doc = attendance_ref.get()
        
        if not attendance_doc.exists:
            raise ValueError("Attendance record not found")
            
        attendance_data = attendance_doc.to_dict()
        slot_id = attendance_data.get('slotId')
        
        if not slot_id:
            raise ValueError("No slot ID found in attendance record")
            
        # Get the slot document
        slot_ref = db.collection('slots').document(slot_id)
        slot_doc = slot_ref.get()
        
        if not slot_doc.exists:
            raise ValueError("Slot not found")
        
        # Update attendance record
        attendance_ref.update({
            'timeOut': firestore.SERVER_TIMESTAMP,
            'status': 'completed'
        })
        
        # Update the slot status
        slot_ref.update({
            'status': 'completed'
        })
        
        print(f"Successfully marked attendance {attendance_id} as exited")
        return True
        
    except Exception as e:
        print(f"Error marking as exited: {str(e)}")
        raise

# Function to get all slots (for general use)
def get_all_slots():
    try:
        # Get all slots
        slots = [doc.to_dict() | {'id': doc.id} for doc in db.collection('slots').stream()]
        
        # Get all attendance records
        attendance_records = {
            doc.get('slotId'): doc.to_dict()
            for doc in db.collection('attendance').stream()
        }
        
        # Merge attendance data with slot data
        for slot in slots:
            if slot['id'] in attendance_records:
                attendance = attendance_records[slot['id']]
                slot['timeIn'] = attendance.get('timeIn')
                slot['timeOut'] = attendance.get('timeOut')
                slot['truckPlate'] = attendance.get('truckPlate')
                # Ensure the status is consistent
                if attendance.get('status') == 'in_terminal':
                    slot['status'] = 'checked_in'
                elif attendance.get('status') == 'completed':
                    slot['status'] = 'completed'
            elif not slot.get('status'):
                slot['status'] = 'available'
                
        return slots
    except Exception as e:
        print(f"Error fetching all slots: {str(e)}")
        raise Exception(f"Error fetching all slots: {str(e)}")

# Function to create a slot
def create_slot(time, product):
    try:
        slot_data = {
            'time': time,
            'product': product,
            'bookedBy': None,
            'status': 'available',  # Add status field
            'created_at': firestore.SERVER_TIMESTAMP
        }
        slot_ref = db.collection('slots').document()
        slot_ref.set(slot_data)
        return slot_ref
    except Exception as e:
        raise Exception(f"Error creating slot: {str(e)}")

# Function to delete a slot
def delete_slot(slot_id):
    try:
        slot_ref = db.collection('slots').document(slot_id)
        slot_ref.delete()
        return True
    except Exception as e:
        raise Exception(f"Error deleting slot: {str(e)}")

# Function to book a slot
def book_slot(slot_id, user_id, plate):
    try:
        slot_ref = db.collection('slots').document(slot_id)
        slot = slot_ref.get()

        if not slot.exists:
            raise Exception("Slot not found")

        if slot.to_dict().get('bookedBy'):
            raise Exception("Slot already booked")

        # Update the slot with the user's ID, status, and vehicle plate
        slot_ref.update({
            'bookedBy': user_id,
            'status': 'booked',
            'truckPlate': plate,
            'booked_at': firestore.SERVER_TIMESTAMP
        })

        return True
    except Exception as e:
        raise Exception(f"Error booking slot: {str(e)}")

# Function to get user bookings by user ID
def get_user_bookings(user_id):
    try:
        # Get all slots booked by this user (including current and completed bookings)
        slots = [
            doc.to_dict() | {'id': doc.id} 
            for doc in db.collection('slots')
            .where('bookedBy', '==', user_id)
            .stream()
        ]
        
        # Get all attendance records for this user's slots
        attendance_records = {}
        for slot in slots:
            attendance_docs = db.collection('attendance').where('slotId', '==', slot['id']).stream()
            for doc in attendance_docs:
                attendance_data = doc.to_dict()
                attendance_data['id'] = doc.id
                attendance_records[slot['id']] = attendance_data
        
        # Merge attendance data with slot data
        for slot in slots:
            if slot['id'] in attendance_records:
                attendance = attendance_records[slot['id']]
                slot['timeIn'] = attendance.get('timeIn')
                slot['timeOut'] = attendance.get('timeOut')
                slot['truckPlate'] = attendance.get('truckPlate') or slot.get('truckPlate')
                # Update status based on attendance
                if attendance.get('status') == 'in_terminal':
                    slot['status'] = 'checked_in'
                elif attendance.get('status') == 'completed':
                    slot['status'] = 'completed'
            # If no attendance record exists, keep the existing status
        
        return slots
    except Exception as e:
        print(f"Error getting user bookings: {str(e)}")
        raise Exception(f"Error getting user bookings: {str(e)}")

# Function to get all attendance records
def get_all_attendance():
    try:
        # Get all attendance records ordered by check-in time
        attendance_records = [
            doc.to_dict() | {'id': doc.id} 
            for doc in db.collection('attendance')
            .order_by('timeIn', direction=firestore.Query.DESCENDING)
            .stream()
        ]
        
        # Get all slots for reference
        slots = {
            doc.id: doc.to_dict()
            for doc in db.collection('slots').stream()
        }
        
        # Merge slot data with attendance records
        for record in attendance_records:
            slot_id = record.get('slotId')
            if slot_id and slot_id in slots:
                slot_data = slots[slot_id]
                record['time'] = slot_data.get('time')
                record['product'] = slot_data.get('product')
                record['bookedBy'] = slot_data.get('bookedBy')
                # Ensure vehicle plate is consistent
                if record.get('status') == 'completed':
                    slot_data['truckPlate'] = None
                else:
                    slot_data['truckPlate'] = record.get('truckPlate')
        
        return attendance_records
    except Exception as e:
        print(f"Error fetching attendance: {str(e)}")
        raise
