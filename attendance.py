# Here's the starting point for attendance.py

from firebase_config import db
from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta

attendance_ref = db.collection("attendance")
slots_ref = db.collection("slots")

def create_attendance(slot_id, truck_plate):
    try:
        # Get slot data first
        slot_doc = slots_ref.document(slot_id).get()
        slot_data = slot_doc.to_dict()

        data = {
            "slotId": slot_id,
            "truckPlate": truck_plate,
            "timeIn": datetime.utcnow(),
            "timeOut": None,
            "status": "in_terminal",
            "product": slot_data.get('product'),  # Add product type
            "bookedBy": slot_data.get('bookedBy'),  # Add company name
            "time": slot_data.get('time')  # Add time slot
        }
        
        # Create attendance record
        doc_ref = attendance_ref.document()
        doc_ref.set(data)
        
        # Update slot status
        slots_ref.document(slot_id).update({
            "status": "checked_in",
            "truckPlate": truck_plate,
            "attendanceId": doc_ref.id
        })
        
        return doc_ref.id
    except Exception as e:
        raise Exception(f"Error creating attendance record: {e}")

def get_active_attendance():
    try:
        return [doc.to_dict() | {"id": doc.id} for doc in attendance_ref.where("status", "==", "in_terminal").stream()]
    except Exception as e:
        raise Exception(f"Error fetching active attendance: {e}")

def get_all_attendance():
    try:
        return [doc.to_dict() | {"id": doc.id} 
                for doc in attendance_ref
                .order_by("timeIn", direction="DESCENDING")
                .stream()]
    except Exception as e:
        raise Exception(f"Error fetching all attendance records: {e}")

def mark_as_exited(attendance_id):
    try:
        # Get attendance record to find slot
        attendance_doc = attendance_ref.document(attendance_id).get()
        attendance_data = attendance_doc.to_dict()
        slot_id = attendance_data.get('slotId')

        # Update attendance record
        attendance_ref.document(attendance_id).update({
            "timeOut": datetime.utcnow(),
            "status": "completed"
        })

        # Update slot status if slot_id exists
        if slot_id:
            slots_ref.document(slot_id).update({
                "status": "completed",
                "truckPlate": None,
                "attendanceId": None
            })

        return True
    except Exception as e:
        raise Exception(f"Error updating attendance: {e}")

def expire_no_show_slots(grace_minutes=15):
    try:
        now = datetime.utcnow()
        slots = slots_ref.stream()
        for slot_doc in slots:
            slot = slot_doc.to_dict()
            if slot.get("bookedBy") and not slot.get("expired"):
                slot_time = datetime.strptime(slot["time"].split(" - ")[0], "%I:%M")
                slot_datetime = now.replace(hour=slot_time.hour, minute=slot_time.minute, second=0, microsecond=0)
                cutoff = slot_datetime + timedelta(minutes=grace_minutes)
                if now > cutoff:
                    slots_ref.document(slot_doc.id).update({
                        "expired": True,
                        "bookedBy": None,
                        "source": None
                    })
    except Exception as e:
        raise Exception(f"Error expiring no-show slots: {e}")

# === views_driver.py ===

views_driver = Blueprint("driver_checkin", __name__)

@views_driver.route("/check-in-form/<slot_id>", methods=["GET", "POST"])
def check_in_form(slot_id):
    if request.method == "POST":
        plate = request.form.get("plate")
        try:
            create_attendance(slot_id, plate)
            flash("Check-in successful. You may now proceed to the terminal.", "success")
            return redirect(url_for("driver_checkin.check_in_form", slot_id=slot_id))
        except Exception as e:
            flash(str(e), "error")
    return render_template("check_in_form.html", slot_id=slot_id)