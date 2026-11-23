from dotenv import load_dotenv
load_dotenv()
import datetime
import os
import uuid
from functools import wraps

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, db, initialize_app
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_HTTPS", "false").lower() == "true",
)

FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "service.json")
FIREBASE_DB_URL = os.getenv(
    "FIREBASE_DB_URL",
    "https://miniproject-42dfe-default-rtdb.europe-west1.firebasedatabase.app/",
)
if not firebase_admin._apps:
    if not os.path.exists(FIREBASE_KEY_PATH):
        raise RuntimeError(f"Firebase key file not found: {FIREBASE_KEY_PATH}")
    initialize_app(credentials.Certificate(FIREBASE_KEY_PATH), {"databaseURL": FIREBASE_DB_URL})


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                if request.path.startswith("/api/") or request.method != "GET":
                    return jsonify({"error": "Unauthorized"}), 403
                return redirect(url_for("home1"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def csrf_required(view):
    """Require same-origin requests for browser-initiated state changes."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                return jsonify({"error": "Invalid request origin"}), 403
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    return render_template("logo.html")


@app.route("/home1")
def home1():
    return render_template("home1.html")


@app.route("/adminlogin", methods=["GET", "POST"])
@csrf_required
def adminlogin():
    if request.method == "GET":
        return render_template("adminlogin.html")
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", data.get("adminid", ""))).strip()
    password = str(data.get("password", ""))
    configured_user = os.getenv("ADMIN_USERNAME", "")
    configured_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    if configured_user and configured_hash and username == configured_user and check_password_hash(configured_hash, password):
        session.clear()
        session["role"] = "admin"
        session["admin"] = username
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@app.route("/admin_dashboard")
@roles_required("admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/mech_open")
def mech_open():
    return render_template("mech_open.html")


@app.route("/open")
def open():
    return render_template("open.html")


@app.route("/mech_dashboard")
@roles_required("mechanic")
def mech_dashboard():
    return render_template("mech_dashboard.html")


@app.route("/open")
def open_page():
    return render_template("open.html")


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/feedback", methods=["GET"])
def feedback():
    return render_template("feedback.html")


@app.route("/customerdashboard")
@roles_required("customer")
def customerdashboard():
    return render_template("customerdashboard.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/register", methods=["POST"])
@csrf_required
def register():
    firstname = request.form.get("firstname", "").strip()
    lastname = request.form.get("lastname", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    vehicle_type = request.form.get("vehicle_type", "")
    if not email or not password or password != confirm_password:
        flash("Check your email and passwords.", "error")
        return redirect(url_for("register_page"))
    existing = db.reference("users").get() or {}
    if any(u.get("email") == email for u in existing.values()):
        flash("Email already registered.", "error")
        return redirect(url_for("register_page"))
    db.reference("users").push({
        "firstname": firstname, "lastname": lastname, "email": email,
        "phone": phone, "password": generate_password_hash(password),
        "vehicle_type": vehicle_type,
    })
    flash("Registration successful!", "success")
    return redirect(url_for("login_page"))


@app.route("/login", methods=["POST"])
@csrf_required
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    users = db.reference("users").get() or {}
    for user in users.values():
        if user.get("email") == email:
            hashed = user.get("password", "")
            if hashed and check_password_hash(hashed, password):
                session.clear()
                session["user"] = email
                session["role"] = "customer"
                return redirect(url_for("customerdashboard"))
            flash("Wrong password!", "error")
            return redirect(url_for("login_page"))
    flash("Email not found.", "error")
    return redirect(url_for("login_page"))


@app.route("/feedback", methods=["POST"])
@csrf_required
def feedback_submit():
    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        return jsonify({"error": "Invalid rating"}), 400
    db.reference("feedbacks").push({
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "message": request.form.get("message"),
        "rating": rating,
    })
    flash("Feedback saved!", "success")
    return redirect(url_for("feedback"))


@app.route("/mech_login", methods=["GET", "POST"])
@csrf_required
def mech_login():
    if request.method == "GET":
        return render_template("mech_login.html")
    data = request.get_json(silent=True) or {}
    mechid = str(data.get("mechid", "")).strip().lower()
    password = str(data.get("password", ""))
    configured_user = os.getenv("MECHANIC_USERNAME", "").lower()
    configured_hash = os.getenv("MECHANIC_PASSWORD_HASH", "")
    if configured_user and configured_hash and mechid == configured_user and check_password_hash(configured_hash, password):
        session.clear()
        session["mechanic"] = mechid
        session["role"] = "mechanic"
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home1"))


@app.route("/api/feedbacks")
@roles_required("admin")
def get_all_feedbacks():
    data = db.reference("feedbacks").get() or {}
    return jsonify(list(data.values()))


@app.route("/addnew", methods=["POST"])
@roles_required("customer")
@csrf_required
def save_vehicle():
    data = request.get_json(silent=True) or {}
    data["user"] = session["user"]
    db.reference("vehicles").push(data)
    return jsonify({"success": True})


@app.route("/api/vehicles")
@roles_required("customer")
def get_vehicles():
    data = db.reference("vehicles").get() or {}
    return jsonify([v for v in data.values() if v.get("user") == session["user"]])


@app.route("/bookservice", methods=["POST"])
@roles_required("customer")
@csrf_required
def book_service():
    data = request.get_json(silent=True) or {}
    booking = {
        "user": session["user"],
        "vehicle_make": data.get("make"),
        "vehicle_model": data.get("model"),
        "service_type": data.get("serviceType"),
        "service_date": data.get("serviceDate"),
        "status": "Pending",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    ref = db.reference("booked_services").push(booking)
    return jsonify({"success": True, "id": ref.key, "message": "Booking added"})


@app.route("/api/admin/update_status/<booking_id>", methods=["PUT"])
@roles_required("admin")
@csrf_required
def update_service_status(booking_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "Status required"}), 400
    ref = db.reference(f"booked_services/{booking_id}")
    if not ref.get():
        return jsonify({"error": "Booking not found"}), 404
    ref.update({"status": new_status})
    return jsonify({"success": True, "message": f"Updated to {new_status}"})


@app.route("/api/bookings")
@roles_required("customer")
def get_bookings():
    data = db.reference("booked_services").get() or {}
    return jsonify({k: v for k, v in data.items() if v.get("user") == session["user"]})


@app.route("/api/admin/bookings")
@roles_required("admin")
def admin_bookings():
    return jsonify(db.reference("booked_services").get() or {})


@app.route("/api/delete_booking/<bid>", methods=["DELETE"])
@roles_required("admin", "customer")
@csrf_required
def delete_booking(bid):
    ref = db.reference(f"booked_services/{bid}")
    booking = ref.get()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if session.get("role") == "customer" and booking.get("user") != session.get("user"):
        return jsonify({"error": "Unauthorized"}), 403
    ref.delete()
    return jsonify({"success": True})


@app.route("/api/customers")
@roles_required("admin")
def get_customers():
    data = db.reference("users").get() or {}
    return jsonify([{k: v for k, v in user.items() if k != "password"} for user in data.values()])


@app.route("/api/mechanics", methods=["GET"])
@roles_required("admin", "mechanic")
def api_get_mechanics():
    data = db.reference("mechanics").get() or {}

    return jsonify([
        {
            "id": mid,
            **{
                k: v for k, v in m.items()
                if k not in ("password",)
            }
        }
        for mid, m in data.items()
    ])

@app.route("/api/mechanics", methods=["POST"])
@roles_required("admin")
@csrf_required
def api_add_mechanic():
    data = request.get_json(silent=True) or {}
    mid = str(uuid.uuid4())
    record = {k: data.get(k) for k in (
        "firstname", "lastname", "email", "phone", "username",
        "services", "status", "profile_pic",
    )}
    if data.get("password"):
        record["password"] = generate_password_hash(str(data["password"]))
    db.reference(f"mechanics/{mid}").set(record)
    return jsonify({"success": True, "id": mid})


@app.route("/api/mechanics/<mid>", methods=["PUT"])
@roles_required("admin")
@csrf_required
def api_update_mechanic(mid):
    data = request.get_json(silent=True) or {}
    allowed = {"firstname", "lastname", "email", "phone", "username", "services", "status", "profile_pic"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if data.get("password"):
        updates["password"] = generate_password_hash(str(data["password"]))
    ref = db.reference(f"mechanics/{mid}")
    if not ref.get():
        return jsonify({"error": "Mechanic not found"}), 404
    if updates:
        ref.update(updates)
    return jsonify({"success": True})


@app.route("/api/mechanics/<mid>", methods=["DELETE"])
@roles_required("admin")
@csrf_required
def api_delete_mechanic(mid):
    db.reference(f"mechanics/{mid}").delete()
    return jsonify({"success": True})


@app.route("/api/assigned_jobs", methods=["GET"])
@roles_required("admin", "mechanic")
def get_assigned_jobs():
    data = db.reference("assigned_jobs").get() or {}
    return jsonify([{"id": jid, **j} for jid, j in data.items()])


@app.route("/api/assigned_jobs", methods=["POST"])
@roles_required("admin")
@csrf_required
def add_assigned_job():
    data = request.get_json(silent=True) or {}
    jid = str(uuid.uuid4())
    db.reference(f"assigned_jobs/{jid}").set(data)
    return jsonify({"success": True, "id": jid})


@app.route("/api/assigned_jobs/<jid>", methods=["PUT"])
@roles_required("admin", "mechanic")
@csrf_required
def update_assigned_job(jid):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in {"Pending", "In Progress", "Completed"}:
        return jsonify({"error": "Invalid status"}), 400
    job_ref = db.reference(f"assigned_jobs/{jid}")
    job_data = job_ref.get()
    if not job_data:
        return jsonify({"error": "Job not found"}), 404
    job_ref.update({"status": new_status})
    booking_id = job_data.get("booking_id")
    if booking_id:
        all_jobs = db.reference("assigned_jobs").get() or {}
        related = [j for j in all_jobs.values() if j.get("booking_id") == booking_id]
        statuses = [j.get("status") for j in related]
        if all(s == "Completed" for s in statuses):
            overall_status = "Completed"
        elif any(s == "In Progress" for s in statuses):
            overall_status = "In Progress"
        else:
            overall_status = "Pending"
        booking_ref = db.reference(f"booked_services/{booking_id}")
        if booking_ref.get():
            booking_ref.update({"status": overall_status})
    return jsonify({
        "success": True,
        "message": f"Status updated to {new_status} and booking synced",
        "booking_id": booking_id,
    })


@app.route("/api/assigned_jobs/<jid>", methods=["DELETE"])
@roles_required("admin")
@csrf_required
def delete_assigned_job(jid):
    db.reference(f"assigned_jobs/{jid}").delete()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
