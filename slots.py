# slots.py
from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from auth import login_required
from firebase_config import get_all_slots, book_slot, get_user_bookings

slots_bp = Blueprint("slots", __name__)

@slots_bp.route("/haulier", endpoint="haulier_dashboard")
@login_required
def haulier_dashboard():
    try:
        all_slots = get_all_slots()
        user_id = session["user"]["uid"]
        
        # Available slots (not booked)
        available_slots = [slot for slot in all_slots if not slot.get('bookedBy')]
        
        # Slots booked by the current user
        my_bookings = get_user_bookings(user_id)

        return render_template(
            "haulier_dashboard.html",
            available_slots=available_slots,
            my_bookings=my_bookings
        )
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template("haulier_dashboard.html", available_slots=[], my_bookings=[])

@slots_bp.route("/book/<slot_id>", methods=["POST"])
@login_required
def book_slot_route(slot_id):
    try:
        user_id = session["user"]["uid"]
        plate = request.form.get("plate")
        
        if not plate:
            flash("Vehicle plate number is required", "error")
            return redirect(url_for("slots.haulier_dashboard"))
            
        book_slot(slot_id, user_id, plate)
        flash("Slot booked successfully", "success")
    except Exception as e:
        flash(f"Error booking slot: {str(e)}", "error")
    
    return redirect(url_for("slots.haulier_dashboard"))
