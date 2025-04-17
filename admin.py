# admin.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from auth import admin_required
from firebase_config import db, get_all_attendance
from datetime import datetime
import traceback

admin_bp = Blueprint("admin", __name__)

# Define full schedule
ALL_TIME_SLOTS = [
    "8:00 - 8:30 AM", "8:30 - 9:00 AM", "9:00 - 9:30 AM", "9:30 - 10:00 AM",
    "10:00 - 10:30 AM", "10:30 - 11:00 AM", "11:00 - 11:30 AM", "11:30 - 12:00 PM",
    "12:00 - 12:30 PM", "12:30 - 1:00 PM", "1:00 - 1:30 PM", "1:30 - 2:00 PM",
    "2:00 - 2:30 PM", "2:30 - 3:00 PM", "3:00 - 3:30 PM", "3:30 - 4:00 PM",
    "4:00 - 4:30 PM", "4:30 - 5:00 PM"
]

@admin_bp.route("/dashboard")
@admin_required
def admin_dashboard():
    try:
        slots_ref = db.collection('slots').stream()
        slots = [doc.to_dict() | {'id': doc.id} for doc in slots_ref]

        # Time filtering (show only time slots that are not already added)
        booked_times = {slot['time'] for slot in slots}
        available_times = [t for t in ALL_TIME_SLOTS if t not in booked_times]

        # Stats summary
        stats = {
            'total_slots': len(slots),  # Total number of slots
            'awaiting_checkin': len([s for s in slots if s.get('status') == 'booked']),
            'in_terminal': len([s for s in slots if s.get('status') == 'checked_in']),
            'completed': len([s for s in slots if s.get('status') == 'completed'])
        }

        attendance_records = get_all_attendance()

        return render_template("admin_dashboard.html",
                               slots=slots,
                               available_times=available_times,
                               stats=stats,
                               attendance_records=attendance_records)
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", 'error')
        return render_template("admin_dashboard.html", 
                               slots=[], 
                               available_times=[], 
                               stats={'total_slots': 0, 'awaiting_checkin': 0, 'in_terminal': 0, 'completed': 0}, 
                               attendance_records=[])

@admin_bp.route("/add_slot", methods=["POST"])
@admin_required
def add_slot():
    try:
        time = request.form.get("time")
        product = request.form.get("product")

        if not time or not product:
            flash('Time and product are required.', 'error')
            return redirect(url_for('admin.admin_dashboard'))

        # Check if the slot already exists
        existing = db.collection('slots').where('time', '==', time).stream()
        if any(True for _ in existing):
            flash('This time slot already exists.', 'error')
            return redirect(url_for('admin.admin_dashboard'))

        # Create new slot with explicit 'available' status
        slot_data = {
            'time': time,
            'product': product,
            'bookedBy': None,
            'status': 'available',  # Explicitly set status as 'available'
            'created_at': datetime.utcnow()
        }
        
        db.collection('slots').add(slot_data)
        flash('Slot added successfully.', 'success')
    except Exception as e:
        print("Error adding slot:", str(e))
        flash(f"Failed to add slot: {str(e)}", 'error')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/delete_slot/<slot_id>", methods=["POST"])
@admin_required
def delete_slot(slot_id):
    try:
        db.collection('slots').document(slot_id).delete()
        flash("Slot deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting slot: {str(e)}", "error")
    return redirect(url_for("admin.admin_dashboard"))
