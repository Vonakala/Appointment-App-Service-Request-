import firebase_admin
from firebase_admin import credentials, auth, db
import os

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

# Admin user details
admin_email = "vonakala@yahoo.com"  # change this
admin_password = "Testing@12"       # change this
admin_name = "Admin"
admin_phone = "+277734570211"

try:
    # Create Firebase Auth user
    user_record = auth.create_user(
        email=admin_email,
        password=admin_password
    )
    uid = user_record.uid
    print(f"Admin user created with UID: {uid}")

    # Add to Realtime Database
    db.reference(f"users/{uid}").set({
        "name": admin_name,
        "email": admin_email,
        "phone": admin_phone,
        "role": "admin"
    })
    print("Admin added to Firebase Realtime Database successfully!")

except Exception as e:
    print("Error creating admin:", e)
