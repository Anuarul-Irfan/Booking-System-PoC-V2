from flask import render_template, flash, redirect, url_for, request, session, Blueprint
from functools import wraps
from firebase_config import db
from attendance import create_attendance, mark_as_exited, get_active_attendance

guard_bp = Blueprint('guard', __name__)

def guard_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        if session['user'].get('role') != 'guard':
            flash('Access denied. Guard privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@guard_bp.route('/dashboard')
@guard_required
def guard_dashboard():
    try:
        # Booked but not yet checked in
        awaiting_checkin = [
            doc.to_dict() | {'id': doc.id}
            for doc in db.collection('slots')
            .where('bookedBy', '!=', None)
            .stream()
            if doc.to_dict().get('status') == 'booked'
        ]

        # Already checked in
        in_terminal = get_active_attendance()

        return render_template("guard_dashboard.html",
                               awaiting_checkin=awaiting_checkin,
                               in_terminal=in_terminal)
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template("guard_dashboard.html",
                               awaiting_checkin=[], in_terminal=[])

@guard_bp.route('/check-in/<slot_id>', methods=['POST'])
@guard_required
def check_in(slot_id):
    try:
        plate = request.form.get('plate')
        if not plate:
            flash("Vehicle plate number is required.", "error")
            return redirect(url_for("guard.guard_dashboard"))

        create_attendance(slot_id, plate)
        flash("Vehicle successfully checked in.", "success")
    except Exception as e:
        flash(f"Error during check-in: {str(e)}", "error")

    return redirect(url_for("guard.guard_dashboard"))

@guard_bp.route('/check-out/<attendance_id>', methods=['POST'])
@guard_required
def check_out(attendance_id):
    try:
        mark_as_exited(attendance_id)
        flash("Vehicle successfully checked out.", "success")
    except Exception as e:
        flash(f"Error during check-out: {str(e)}", "error")

    return redirect(url_for("guard.guard_dashboard"))
