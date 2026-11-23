from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import firebase_admin
from firebase_admin import credentials, db, initialize_app
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import uuid
import os

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

FIREBASE_KEY_PATH = "service.json"
FIREBASE_DB_URL = "https://miniproject-42dfe-default-rtdb.europe-west1.firebasedatabase.app/"

# Initialize Firebase once
if not firebase_admin._apps:
    if not os.path.exists(FIREBASE_KEY_PATH):
        raise RuntimeError(f"Firebase key file not found: {FIREBASE_KEY_PATH}")
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})


# ROUTES
@app.route("/")
def home():
    return render_template("logo.html")

@app.route("/home1")
def home1():
    return render_template("home1.html")

@app.route("/adminlogin")
def adminlogin():
    return render_template("adminlogin.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")

@app.route("/mech_open")
def mech_open():
    return render_template("mech_open.html")

@app.route("/mech_dashboard")
def mech_dashboard():
    return render_template("mech_dashboard.html")

@app.route("/open")
def open():
    return render_template("open.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

@app.route("/customerdashboard")
def customerdashboard():
    return render_template("customerdashboard.html")

@app.route("/services")
def services():
    return render_template("services.html")


#  Registration
@app.route("/register", methods=["POST"])
def register():
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    vehicle_type = request.form.get("vehicle_type")

    if password != confirm_password:
        flash("Passwords do not match!", "error")
        return redirect(url_for("register_page"))

    hashed_password = generate_password_hash(password)
    db.reference("users").push({
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "phone": phone,
        "password": hashed_password,
        "vehicle_type": vehicle_type
    })

    flash("Registration successful!", "success")
    return redirect(url_for("login_page"))


#  Login
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    ref = db.reference("users")
    users = ref.get()

    if not users:
        flash("No registered users found.", "error")
        return redirect(url_for("login_page"))

    for key, user in users.items():
        if user.get("email") == email:
            if check_password_hash(user.get("password"), password):
                session["user"] = email
                return redirect(url_for("customerdashboard"))
            else:
                flash("Wrong password!", "error")
                return redirect(url_for("login_page"))

    flash("Email not found.", "error")
    return redirect(url_for("login_page"))


#  Feedback
@app.route("/feedback", methods=["POST"])
def feedback_submit():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")
    rating = request.form.get("rating")

    db.reference("feedbacks").push({
        "name": name,
        "email": email,
        "message": message,
        "rating": int(rating)
    })

    flash("Feedback saved!", "success")
    return redirect(url_for("feedback"))


# Mechanic Login (Shared)
@app.route("/mech_login", methods=["GET", "POST"])
def mech_login():
    if request.method == "GET":
        return render_template("mech_login.html")

    data = request.get_json()
    mechid = data.get("mechid")
    password = data.get("password")

    if mechid.lower() == "mechanic" and password == "AK@12345":
        session["mechanic"] = mechid
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 401


#  Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home1"))


# API: GET Feedback
@app.route("/api/feedbacks")
def get_all_feedbacks():
    data = db.reference("feedbacks").get()
    return jsonify(list(data.values())) if data else jsonify([])


# Save Vehicle
@app.route("/addnew", methods=["POST"])
def save_vehicle():
    if "user" not in session:
        return jsonify({"error": "Login required"}), 401
    data = request.get_json()
    data["user"] = session["user"]
    db.reference("vehicles").push(data)
    return jsonify({"success": True})


#  GET Vehicles for customer
@app.route("/api/vehicles")
def get_vehicles():
    if "user" not in session:
        return jsonify([])
    current = session["user"]
    data = db.reference("vehicles").get() or {}
    user_vehicles = [v for v in data.values() if v.get("user") == current]
    return jsonify(user_vehicles)


#  Book service
@app.route("/bookservice", methods=["POST"])
def book_service():
    if "user" not in session:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json()
    booking = {
        "user": session["user"],
        "vehicle_make": data.get("make"),
        "vehicle_model": data.get("model"),
        "service_type": data.get("serviceType"),
        "service_date": data.get("serviceDate"),
        "status": "Pending",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    ref = db.reference("booked_services").push(booking)
    booking_id = ref.key
    return jsonify({"success": True, "id": booking_id, "message": "Booking added"})


# Admin updates booking status
@app.route("/api/admin/update_status/<booking_id>", methods=["PUT"])
def update_service_status(booking_id):
    data = request.get_json()
    new_status = data.get("status")

    if not new_status:
        return jsonify({"error": "Status required"}), 400

    ref = db.reference(f"booked_services/{booking_id}")
    if not ref.get():
        return jsonify({"error": "Booking not found"}), 404

    ref.update({"status": new_status})
    return jsonify({"success": True, "message": f"Updated to {new_status}"})


#  Customer view bookings
@app.route("/api/bookings")
def get_bookings():
    if "user" not in session:
        return jsonify({})
    current = session["user"]
    data = db.reference("booked_services").get() or {}
    filtered = {k: v for k, v in data.items() if v.get("user") == current}
    return jsonify(filtered)


#  ADMIN bookings
@app.route("/api/admin/bookings")
def admin_bookings():
    return jsonify(db.reference("booked_services").get() or {})


#  Delete booking
@app.route("/api/delete_booking/<bid>", methods=["DELETE"])
def delete_booking(bid):
    db.reference(f"booked_services/{bid}").delete()
    return jsonify({"success": True})


# GET Customers (Admin)
@app.route("/api/customers")
def get_customers():
    data = db.reference("users").get()
    return jsonify(list(data.values())) if data else jsonify([])


#  MECHANICS CRUD
@app.route("/api/mechanics", methods=["GET"])
def api_get_mechanics():
    ref = db.reference("mechanics").get()
    if not ref:
        return jsonify([])
    mechanics_list = []
    for mid, m in ref.items():
        m["id"] = mid
        mechanics_list.append(m)
    return jsonify(mechanics_list)


@app.route("/api/mechanics", methods=["POST"])
def api_add_mechanic():
    data = request.get_json()
    mid = str(uuid.uuid4())
    db.reference(f"mechanics/{mid}").set({
        "firstname": data.get("firstname"),
        "lastname": data.get("lastname"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "username": data.get("username"),
        "password": data.get("password"),
        "services": data.get("services"),
        "status": data.get("status"),
        "profile_pic": data.get("profile_pic")
    })
    return jsonify({"success": True, "id": mid})


@app.route("/api/mechanics/<mid>", methods=["PUT"])
def api_update_mechanic(mid):
    data = request.get_json()
    db.reference(f"mechanics/{mid}").update(data)
    return jsonify({"success": True})


@app.route("/api/mechanics/<mid>", methods=["DELETE"])
def api_delete_mechanic(mid):
    db.reference(f"mechanics/{mid}").delete()
    return jsonify({"success": True})


# ASSIGNED JOBS — stored in Firebase
@app.route("/api/assigned_jobs", methods=["GET"])
def get_assigned_jobs():
    data = db.reference("assigned_jobs").get()
    if not data:
        return jsonify([])
    result = []
    for jid, j in data.items():
        j["id"] = jid
        result.append(j)
    return jsonify(result)


@app.route("/api/assigned_jobs", methods=["POST"])
def add_assigned_job():
    data = request.get_json()
    jid = str(uuid.uuid4())
    db.reference(f"assigned_jobs/{jid}").set(data)
    return jsonify({"success": True, "id": jid})


# UPDATE ASSIGNED JOB STATUS (Mechanic updates → auto-sync booking)
@app.route("/api/assigned_jobs/<jid>", methods=["PUT"])
def update_assigned_job(jid):
    data = request.get_json()
    new_status = data.get("status")

    if not new_status:
        return jsonify({"error": "Status required"}), 400

    job_ref = db.reference(f"assigned_jobs/{jid}")
    job_data = job_ref.get()

    if not job_data:
        return jsonify({"error": "Job not found"}), 404

    #  Update the specific assigned job status
    job_ref.update({"status": new_status})

    # Recalculate booking's overall status
    booking_id = job_data.get("booking_id")
    if booking_id:
        all_jobs = db.reference("assigned_jobs").get() or {}
        related_jobs = [j for j in all_jobs.values() if j.get("booking_id") == booking_id]

        statuses = [j.get("status") for j in related_jobs]
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
        "booking_id": booking_id
    })


# DELETE ASSIGNED JOB
@app.route("/api/assigned_jobs/<jid>", methods=["DELETE"])
def delete_assigned_job(jid):
    db.reference(f"assigned_jobs/{jid}").delete()
    return jsonify({"success": True})


#  RUN SERVER
if __name__ == "__main__":
    app.run(debug=True)
