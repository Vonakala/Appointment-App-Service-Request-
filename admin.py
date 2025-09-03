import firebase_admin
from firebase_admin import credentials, auth, db
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })


# Admin user details
print("You are about to create a new administrator into Service Request Database !!!!\n")
admin_email = str(input("Provide new admin email address : ")) 
admin_password = str(input("Provide new admin password : "))      
admin_name = str(input("Provide new admin name : "))
admin_surname = str(input("Provide new admin surname : "))
admin_phone = int(input("Provide new admin phone number : "))

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
