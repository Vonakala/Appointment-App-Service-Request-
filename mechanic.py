from flask import Flask, render_template, request, flash, redirect, url_for
import firebase_admin
from firebase_admin import credentials, auth, db
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # needed for flash messages

# Path to your service account
SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(__file__),
    "service-app-1881f-firebase-adminsdk-fbsvc-17f55849db.json"
)

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://service-app-1881f-default-rtdb.firebaseio.com/"
    })

@app.route("/", methods=["GET", "POST"])
def create_mechanic():
    if request.method == "POST":
        name = request.form.get("name")
        surname = request.form.get("surname")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")

        try:
            # Create user in Firebase Auth
            user_record = auth.create_user(
                email=email,
                password=password
            )
            uid = user_record.uid

            # Add user to Firebase Realtime Database
            db.reference(f"users/{uid}").set({
                "name": name,
                "surname": surname,
                "email": email,
                "phone": phone,
                "role": "mechanic"
            })

            flash("Mechanic created successfully!", "success")
            return redirect(url_for("create_mechanic"))

        except Exception as e:
            flash(f"Error creating mechanic: {e}", "error")
            return redirect(url_for("create_mechanic"))

    return render_template("create_mechanic.html")

if __name__ == "__main__":
    app.run(debug=True)
