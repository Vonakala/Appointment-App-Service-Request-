from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

client = Client(TWILIO_SID, TWILIO_TOKEN)

TO_NUMBER = "+27734570211"  # Must be verified on Twilio if trial account
message = client.messages.create(
    body="Test SMS from Flask app",
    from_=TWILIO_NUMBER,
    to=TO_NUMBER
)

print(f"SMS sent! SID: {message.sid}")
