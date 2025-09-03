from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import firebase_admin
from firebase_admin import credentials, auth, db
import os
import re
from dotenv import load_dotenv
import secrets
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# loading sensitive and hidden data from the .env file
load_dotenv()

FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
#getting admin
ADMINS = [
    {"email": os.environ.get("ADMIN_EMAIL"), "phone": os.environ.get("ADMIN_PHONE")}
]

# flask app
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# initializing firebase
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })
    print("Firebase initialized")


if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })
    print("Firebase initialized")

# managing login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# user class
# Users get stored in this class when they signup
class User(UserMixin):
    def __init__(self, uid, email=None, role=None, name=None, surname=None, phone=None):
        self.id = uid
        self.email = email
        self.role = role
        self.name = name
        self.surname = surname
        self.phone = phone

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = db.reference(f"users/{user_id}").get()
        if user_data:
            return User(
                uid=user_id,
                email=user_data.get("email"),
                role=user_data.get("role"),
                name=user_data.get("name"),
                surname=user_data.get("surname"),
                phone=user_data.get("phone")
            )
    except Exception as e:
        print("❌ load_user failed:", e)
    return None

# validating password
def is_valid_password(password):
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$'
    return re.match(pattern, password)

# hidding user dashboards
# encrypting landing pages after a successful login 
HASHES = {
    "client_dashboard": "/client",
    "mechanic_dashboard": "/mechanic",
    "admin_dashboard": "/admin",
    "new_mechanic": "/new_mechanic",
    "assign_mechanic": "/assign_mechanic"
}


# routing to help with navigation
@app.route("/")
def index():
    return render_template("home.html")

# registering a client user
# Clients signup before they can make requests. This involves only a client
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        surname = request.form.get("surname")
        gender = request.form.get("gender")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role", "client")

        if not all([name, surname, gender, email, phone, password, confirm_password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if not is_valid_password(password):
            flash("Password must be at least 8 characters, include uppercase, lowercase, number, and special character.", "danger")
            return render_template("register.html")

        try:
            existing_user = auth.get_user_by_email(email)
            if existing_user:
                flash("Email already registered. Please login.", "danger")
                return render_template("register.html")
        except auth.UserNotFoundError:
            pass
        except Exception as e:
            flash(f"Error checking email: {e}", "danger")
            return render_template("register.html")

        try:
            user_record = auth.create_user(email=email, password=password)
            db.reference(f"users/{user_record.uid}").set({
                "name": name,
                "surname": surname,
                "gender": gender,
                "email": email,
                "phone": phone,
                "role": role
            })
            flash("User registered successfully! You can now login.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
            return render_template("register.html")

    return render_template("register.html")

# --- LOGIN ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            user_record = auth.get_user_by_email(email)
            user_info = db.reference(f'users/{user_record.uid}').get()
            if not user_info:
                flash("User not found in database.", "danger")
                return redirect(url_for("login"))

            role = user_info.get("role")
            login_user(User(
                uid=user_record.uid,
                email=email,
                role=role,
                name=user_info.get("name"),
                surname=user_info.get("surname"),
                phone=user_info.get("phone")
            ))
            flash("Logged in successfully!", "success")

            if role == "client":
                return redirect(HASHES["client_dashboard"])
            elif role == "mechanic":
                return redirect(HASHES["mechanic_dashboard"])
            elif role == "admin":
                return redirect(HASHES["admin_dashboard"])
            else:
                flash("Unknown role.", "danger")
                return redirect(url_for("login"))

        except Exception as e:
            flash(f"Login failed: {e}", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

# --- LOGOUT ---
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))

@app.route(HASHES["client_dashboard"])
@login_required
def client_dashboard():
    if current_user.role != "client":
        flash("Access denied", "danger")
        return redirect(url_for("login"))

    bookings = db.reference("serviceRequests").order_by_child("client_id").equal_to(current_user.id).get() or {}
    users = db.reference("users").get() or {}

    # Add mechanic info to bookings
    for key, booking in bookings.items():
        mech_id = booking.get("assigned_mechanic")
        if mech_id and mech_id in users:
            mech = users[mech_id]
            booking["assigned_mechanic_name"] = f"{mech.get('name')} {mech.get('surname')}"
            booking["assigned_mechanic_phone"] = mech.get("phone")
        else:
            booking["assigned_mechanic_name"] = "Not assigned"
            booking["assigned_mechanic_phone"] = "-"

    return render_template("client.html", user=current_user, bookings=bookings, google_maps_api_key=GOOGLE_MAPS_API_KEY)


# --- MECHANIC DASHBOARD ---
@app.route(HASHES["mechanic_dashboard"])
@login_required
def mechanic_dashboard():
    if current_user.role != "mechanic":
        flash("Access denied", "danger")
        return redirect(url_for("login"))
    bookings = db.reference("serviceRequests").order_by_child("assigned_mechanic").equal_to(current_user.id).get() or {}
    return render_template("mechanic.html", user=current_user, bookings=bookings)

# --- ADMIN DASHBOARD ---
@app.route(HASHES["admin_dashboard"])
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("login"))
    bookings = db.reference("serviceRequests").get() or {}
    users = db.reference("users").get() or {}
    mechanics = {uid: info for uid, info in users.items() if info.get("role") == "mechanic"}
    return render_template("admin.html", user=current_user, bookings=bookings, mechanics=mechanics)
    
# Helper functions for notifications
def send_email(to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)


# --- Book Service Route ---
@app.route("/book_service", methods=["POST"])
@login_required
def book_service():
    if current_user.role != "client":
        flash("Access denied", "danger")
        return redirect(url_for("login"))

    # Get form data
    address = request.form.get("address")
    vehicle = request.form.get("vehicle")
    make_model = request.form.get("make_model")
    category = request.form.get("category")
    service_date = request.form.get("service_date")
    service_time = request.form.get("service_time")
    description = request.form.get("description")

    # Validate required fields
    if not all([address, vehicle, make_model, category, service_date, service_time, description]):
        flash("All fields are required.", "danger")
        return redirect(HASHES["client_dashboard"])

    # Combine date and time
    try:
        service_datetime_str = f"{service_date} {service_time}"
        service_datetime = datetime.strptime(service_datetime_str, "%Y-%m-%d %H:%M")
        if service_datetime < datetime.now():
            flash("Selected date and time cannot be in the past.", "danger")
            return redirect(HASHES["client_dashboard"])
    except ValueError:
        flash("Invalid date or time format.", "danger")
        return redirect(HASHES["client_dashboard"])

    # Generate reference number
    reference_number = "REF-" + secrets.token_hex(5).upper()

    # Save request to Firebase
    booking_ref = db.reference("serviceRequests").push()
    booking_ref.set({
        "reference_number": reference_number,
        "client_id": current_user.id,
        "name": current_user.name,
        "surname": current_user.surname,
        "phone": current_user.phone,
        "email": current_user.email,
        "address": address,
        "vehicle": vehicle,
        "make_model": make_model,
        "category": category,
        "service_datetime": service_datetime_str,
        "status": "pending",
        "description": description,
        "assigned_mechanic": None,
        "timestamp": datetime.now().isoformat()
    })

    print(f"Service request saved: {reference_number}")

    # Admins list
    ADMINS = [
        {"email": os.environ.get("ADMIN_EMAIL"), "phone": os.environ.get("ADMIN_PHONE")}
    ]

    # Prepare email/SMS content
    subject_admin = "New Service Request"
    body_admin = (
        f"New service request received:\n"
        f"Reference: {reference_number}\n"
        f"Client: {current_user.name} {current_user.surname}\n"
        f"Vehicle: {vehicle}\n"
        f"Category: {category}\n"
        f"Date/Time: {service_datetime_str}\n"
        f"Address: {address}\n"
        f"Description: {description}"
    )

    subject_client = "Service Request Received"
    body_client = (
        f"Hi {current_user.name}, your service request has been received successfully.\n"
        f"Reference: {reference_number}\n"
        f"Vehicle: {vehicle}\n"
        f"Category: {category}\n"
        f"Date/Time: {service_datetime_str}\n"
        f"Address: {address}\n"
        f"Description: {description}"
    )

    # Send notification to admins
    for admin in ADMINS:
        if not admin['email'] or not admin['phone']:
            print(f"Admin email/phone not set: {admin}")
            continue
        try:
            send_email(admin['email'], subject_admin, body_admin)
        except Exception as e:
            print(f"Failed to send email to admin {admin['email']}: {e}")

    # Send notification to client
    try:
        send_email(current_user.email, subject_client, body_client)
    except Exception as e:
        print(f"Failed to send email to client {current_user.email}: {e}")

    flash(f"Service booked successfully! Reference: {reference_number}", "success")
    return redirect(HASHES["client_dashboard"])


# Logged in Administrator can add mechanic
@app.route(HASHES["new_mechanic"], methods=["GET", "POST"])
@login_required
def newmechanic():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("name")
        surname = request.form.get("surname")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not all([name, surname, email, phone, password, confirm_password]):
            flash("All fields are required.", "danger")
            return render_template("newmechanic.html")
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("newmechanic.html")

        try:
            existing_user = auth.get_user_by_email(email)
            if existing_user:
                flash("Email already exists.", "danger")
                return render_template("newmechanic.html")
        except auth.UserNotFoundError:
            pass
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return render_template("newmechanic.html")

        try:
            user_record = auth.create_user(email=email, password=password)
            db.reference(f"users/{user_record.uid}").set({
                "name": name,
                "surname": surname,
                "email": email,
                "phone": phone,
                "role": "mechanic"
            })
            flash("Mechanic created successfully!", "success")
            return redirect(HASHES["admin_dashboard"])
        except Exception as e:
            flash(f"Failed to create mechanic: {e}", "danger")
            return render_template("newmechanic.html")
    return render_template("newmechanic.html")


# Assigning a mechanic to a selected request.
# Both Mechanic and client (Requester) will receive nootifaction after the administrator has assigned a mechanic 
@app.route(HASHES["assign_mechanic"], methods=["POST"])
@login_required
def assign_mechanic():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("login"))

    booking_id = request.form.get("booking_id")
    mechanic_id = request.form.get("mechanic_id")

    if not booking_id or not mechanic_id:
        flash("Booking ID and Mechanic must be selected.", "danger")
        return redirect(HASHES["admin_dashboard"])

    try:
        # Update the booking in Firebase
        booking_ref = db.reference(f"serviceRequests/{booking_id}")
        booking_ref.update({
            "assigned_mechanic": mechanic_id,
            "status": "assigned"
        })

        # Get booking details
        booking = booking_ref.get()
        client_email = booking.get("email")
        client_phone = booking.get("phone")
        vehicle = booking.get("vehicle")
        category = booking.get("category")
        service_datetime = booking.get("service_datetime")
        address = booking.get("address")
        client_name = booking.get("name")
        description = booking.get("description")

        # Get mechanic details
        mechanic = db.reference(f"users/{mechanic_id}").get()
        mechanic_email = mechanic.get("email")
        mechanic_phone = mechanic.get("phone")
        mechanic_name = mechanic.get("name")

        # sending notications to respective users
        # Email/SMS content for client
        client_subject = "Mechanic Assigned"
        client_body = f"Hi {client_name},\n\nA mechanic has been assigned to your service request:\nReference: {booking.get('reference_number')}\nMechanic: {mechanic_name}\nVehicle: {vehicle}\nCategory: {category}\nDate/Time: {service_datetime}\nAddress: {address}\n\nThank you!"

        # Email/SMS content for mechanic
        mech_subject = "New Service Assigned"
        mech_body = f"Hi {mechanic_name},\n\nYou have been assigned to a new service request:\nReference: {booking.get('reference_number')}\nClient: {client_name}\nVehicle: {vehicle}\nCategory: {category}\n\nDescription: {description}\n\nDate/Time: {service_datetime}\nAddress: {address}\nPhone: {client_phone}\nEmail: {client_email}\n\nPlease contact the client if needed."

        # sending to client
        try:
            send_email(client_email, client_subject, client_body)
        except Exception as e:
            print(f"Failed to notify client: {e}")

        # sending to mechanic
        try:
            send_email(mechanic_email, mech_subject, mech_body)
        except Exception as e:
            print(f"Failed to notify mechanic: {e}")

        flash("Mechanic assigned successfully! Notifications sent to client and mechanic.", "success")

    except Exception as e:
        flash(f"Failed to assign mechanic: {e}", "danger")

    return redirect(HASHES["admin_dashboard"])


# entry point of the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
