from flask import Blueprint, render_template, request, redirect, url_for, flash
from firebase_config import create_attendance  # Corrected import path for create_attendance function

views_driver = Blueprint("driver_checkin", __name__)

@views_driver.route("/check-in-form/<slot_id>", methods=["GET", "POST"])
def check_in_form(slot_id):
    if request.method == "POST":
        plate = request.form.get("plate")
        try:
            # Call create_attendance from terminal_checkin_system
            create_attendance(slot_id, plate)
            flash("Check-in successful. You may now proceed to the terminal.", "success")
            return redirect(url_for("driver_checkin.check_in_form", slot_id=slot_id))
        except Exception as e:
            flash(str(e), "error")
    return render_template("check_in_form.html", slot_id=slot_id)
