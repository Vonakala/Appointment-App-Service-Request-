# Service Request / Appointment Booking App

A web application for **Lure Mobile Mechanics** that allows clients to request vehicle repair or service appointments, while administrators can assign mechanics and send notifications. Mechanic only view and receives requests and notications about their assigned requests.  

This project is built with **Flask**, **Firebase Realtime Database**, and **Google Maps API**.  

---

# Features

- **Client Features**
  - Register and log in securely  
  - Book service/appointment requests  
  - Pin service location using Google Maps  
  - Receive confirmation of bookings  

- **Admin Features**
  - Manage clients and mechanics  
  - Assign service requests to mechanics  
  - Send SMS and email notifications  
  - Track all service requests

  Note: Admin is only added by running the attached admin.py script that only runs on a console.

- **Mechanic Features**
  - Receive assigned jobs with location details  
  - View client information for service requests  

---

# Technologies Used

- **Backend**: Python (Flask)  
- **Frontend**: HTML, CSS (Bootstrap), JavaScript  
- **Database**: Firebase Realtime Database  
- **Maps & Location**: Google Maps JavaScript API, Geolocation, Places Autocomplete  
- **Notifications**: Email (SMTP) & SMS (Twilio)  

---

#Installation & Setup

# 1. Clone the Repository
```bash
git clone https://github.com/Vonakala/serviceRequest_app-Appointment-.git
cd serviceRequest_app-Appointment-
