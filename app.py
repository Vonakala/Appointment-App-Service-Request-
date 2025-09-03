from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import firebase_admin
from firebase_admin import credentials, auth, db
import os
import re
from dotenv import load_dotenv
import secrets
from datetime import datetime
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText


# ------------------------------
# LOAD ENV VARIABLES
# ------------------------------
load_dotenv()

FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")

ADMINS = [
    {"email": os.environ.get("ADMIN1_EMAIL"), "phone": os.environ.get("ADMIN1_PHONE")},
    {"email": os.environ.get("ADMIN2_EMAIL"), "phone": os.environ.get("ADMIN2_PHONE")}
]

# ------------------------------
# FLASK APP
# ------------------------------
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# ------------------------------
# FIREBASE INITIALIZATION
# ------------------------------
SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(__file__),
    "service-app-1881f-firebase-adminsdk-fbsvc-17f55849db.json"
)

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://service-app-1881f-default-rtdb.firebaseio.com/"
    })
    print("✅ Firebase initialized")

# ------------------------------
# LOGIN MANAGER
# ------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ------------------------------
# USER CLASS
# ------------------------------
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

# ------------------------------
# PASSWORD VALIDATION
# ------------------------------
def is_valid_password(password):
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$'
    return re.match(pattern, password)

# ------------------------------
# HASHED ROUTES
# ------------------------------
HASHES = {
    "client_dashboard": "/c" + secrets.token_hex(4),
    "mechanic_dashboard": "/m" + secrets.token_hex(4),
    "admin_dashboard": "/a" + secrets.token_hex(4),
    "new_mechanic": "/n" + secrets.token_hex(4),
    "assign_mechanic": "/as" + secrets.token_hex(4)
}

# ------------------------------
# ROUTES
# ------------------------------
@app.route("/")
def index():
    return render_template("home.html")

# --- REGISTER ---
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
    
@app.route("/process_requests")
@login_required
def process_requests():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("login"))

    ROOT_DIR = os.path.dirname(__file__)
    CLIENT_REQUESTS_FILE = os.path.join(ROOT_DIR, "client_requests.txt")
    CONFIRMED_REQUESTS_FILE = os.path.join(ROOT_DIR, "confirmed_requests.txt")

    if not os.path.exists(CLIENT_REQUESTS_FILE):
        flash("No client requests file found.", "warning")
        return redirect(HASHES["admin_dashboard"])

    with open(CLIENT_REQUESTS_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not lines:
        flash("No requests to process.", "warning")
        return redirect(HASHES["admin_dashboard"])

    processed_count = 0
    processed_list = []
    with open(CONFIRMED_REQUESTS_FILE, "a") as f:
        for line in lines:
            timestamp = datetime.now().isoformat()
            f.write(f"{timestamp} - {line}\n")
            processed_count += 1
            processed_list.append(line)

    # Clear the original client requests file after processing
    open(CLIENT_REQUESTS_FILE, "w").close()

    # Prepare flash message (show max 5 requests)
    preview_list = processed_list[:5]
    more_count = processed_count - len(preview_list)
    preview_text = "<br>".join(preview_list)
    if more_count > 0:
        preview_text += f"<br>...and {more_count} more requests."

    flash(f"Processed {processed_count} client requests successfully!<br>{preview_text}", "success")
    return redirect(HASHES["admin_dashboard"])

    



# --- Helper functions ---
def send_email(to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "vonakalamongwe@gmail.com"  # can be your email
    msg['To'] = to
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("vonakalamongwe@gmail.com", EMAIL_PASSWORD)
        server.send_message(msg)

def send_sms(to, message):
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(
        body=message,
        from_="+27734570211",  # replace with your Twilio number
        to=to
    )

# --- Book_service route ---
@app.route("/book_service", methods=["POST"])
@login_required
def book_service():
    if current_user.role != "client":
        flash("Access denied", "danger")
        return redirect(url_for("login"))

    # 1️⃣ Get form data
    address = request.form.get("address")
    vehicle = request.form.get("vehicle")
    make_model = request.form.get("make_model")
    category = request.form.get("category")
    service_date = request.form.get("service_date")
    service_time = request.form.get("service_time")

    # 2️⃣ Validate required fields
    if not all([address, vehicle, make_model, category, service_date, service_time]):
        flash("All fields are required.", "danger")
        return redirect(HASHES["client_dashboard"])

    # 3️⃣ Combine date and time
    try:
        service_datetime_str = f"{service_date} {service_time}"
        service_datetime = datetime.strptime(service_datetime_str, "%Y-%m-%d %H:%M")
        if service_datetime < datetime.now():
            flash("Selected date and time cannot be in the past.", "danger")
            return redirect(HASHES["client_dashboard"])
    except ValueError:
        flash("Invalid date or time format.", "danger")
        return redirect(HASHES["client_dashboard"])

    # 4️⃣ Generate reference number
    reference_number = "REF-" + secrets.token_hex(5).upper()

    # 5️⃣ Save to Firebase
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
        "assigned_mechanic": None,
        "timestamp": datetime.now().isoformat()
    })

    print(f"✅ Service request saved: {reference_number}")

    # 6️⃣ Prepare notifications
    admins = [
        {"email": os.environ.get("ADMIN1_EMAIL"), "phone": os.environ.get("ADMIN1_PHONE")},
        {"email": os.environ.get("ADMIN2_EMAIL"), "phone": os.environ.get("ADMIN2_PHONE")}
    ]

    subject_admin = "New Service Request"
    body_admin = (
        f"New service request received:\n"
        f"Reference: {reference_number}\n"
        f"Client: {current_user.name} {current_user.surname}\n"
        f"Vehicle: {vehicle}\n"
        f"Category: {category}\n"
        f"Date/Time: {service_datetime_str}\n"
        f"Address: {address}"
    )

    subject_client = "Service Request Confirmed"
    body_client = (
        f"Hi {current_user.name}, your service request has been received successfully.\n"
        f"Reference: {reference_number}\n"
        f"Vehicle: {vehicle}\n"
        f"Category: {category}\n"
        f"Date/Time: {service_datetime_str}\n"
        f"Address: {address}"
    )

    # 7️⃣ Send notifications to admins
    for admin in admins:
        if not admin['email'] or not admin['phone']:
            print(f"⚠️ Admin email/phone not set: {admin}")
            continue
        try:
            print(f"Sending email to {admin['email']}")
            send_email(admin['email'], subject_admin, body_admin)
        except Exception as e:
            print(f"❌ Failed to send email to admin {admin['email']}: {e}")

        try:
            print(f"Sending SMS to {admin['phone']}")
            send_sms(admin['phone'], body_admin)
        except Exception as e:
            print(f"❌ Failed to send SMS to admin {admin['phone']}: {e}")

    # 8️⃣ Send notifications to client
    try:
        print(f"Sending email to client {current_user.email}")
        send_email(current_user.email, subject_client, body_client)
    except Exception as e:
        print(f"❌ Failed to send email to client {current_user.email}: {e}")

    try:
        print(f"Sending SMS to client {current_user.phone}")
        send_sms(current_user.phone, body_client)
    except Exception as e:
        print(f"❌ Failed to send SMS to client {current_user.phone}: {e}")

    flash(f"Service booked successfully! Reference: {reference_number}", "success")
    return redirect(HASHES["client_dashboard"])





# --- CREATE NEW MECHANIC ---
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

# --- ASSIGN MECHANIC ---
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

        # Get mechanic details
        mechanic = db.reference(f"users/{mechanic_id}").get()
        mechanic_email = mechanic.get("email")
        mechanic_phone = mechanic.get("phone")
        mechanic_name = mechanic.get("name")

        # --- Notifications ---
        # Email/SMS content for client
        client_subject = "Mechanic Assigned"
        client_body = f"Hi {client_name},\n\nA mechanic has been assigned to your service request:\nReference: {booking.get('reference_number')}\nMechanic: {mechanic_name}\nVehicle: {vehicle}\nCategory: {category}\nDate/Time: {service_datetime}\nAddress: {address}\n\nThank you!"

        # Email/SMS content for mechanic
        mech_subject = "New Service Assigned"
        mech_body = f"Hi {mechanic_name},\n\nYou have been assigned to a new service request:\nReference: {booking.get('reference_number')}\nClient: {client_name}\nVehicle: {vehicle}\nCategory: {category}\nDate/Time: {service_datetime}\nAddress: {address}\nPhone: {client_phone}\nEmail: {client_email}\n\nPlease contact the client if needed."

        # Send to client
        try:
            send_email(client_email, client_subject, client_body)
            send_sms(client_phone, client_body)
        except Exception as e:
            print(f"Failed to notify client: {e}")

        # Send to mechanic
        try:
            send_email(mechanic_email, mech_subject, mech_body)
            send_sms(mechanic_phone, mech_body)
        except Exception as e:
            print(f"Failed to notify mechanic: {e}")

        flash("Mechanic assigned successfully! Notifications sent to client and mechanic.", "success")

    except Exception as e:
        flash(f"Failed to assign mechanic: {e}", "danger")

    return redirect(HASHES["admin_dashboard"])


# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
