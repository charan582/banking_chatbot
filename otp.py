import random
import time
import smtplib


otp_storage = {}

def generate_otp(user_id):
    otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
    expiry_time = time.time() + 300  # OTP valid for 5 minutes (300 seconds)
    otp_storage[user_id] = {"otp": otp, "expiry": expiry_time}
    return otp

def send_otp(user_id, communication_channel="email"):
    otp = generate_otp(user_id)
    if communication_channel == "email":
        email = "charandatta582@gmail.com"
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("1da21cs040.cs@drait.edu.in", "lkgyxthfjgbjboya")
            message = f"Subject: Your OTP\n\nYour OTP is: {otp}"
            server.sendmail("1da21cs040.cs@drait.edu.in", email, message)
            server.quit()
    return "An OTP has been sent to your registered email. Please provide the OTP to proceed."
        
def verify_otp(user_id, user_input_otp):
    stored_otp_data = otp_storage.get(user_id)
    print(stored_otp_data)

    if stored_otp_data:
        current_time = time.time()
        if current_time > stored_otp_data["expiry"]:
            del otp_storage[user_id]  # Remove expired OTP
            return False, "OTP has expired. Please request a new one.\n"

        if stored_otp_data["otp"] == user_input_otp:
            del otp_storage[user_id]  # Remove OTP after successful verification
            return True, "OTP verified successfully.\n"

    return False, "Invalid OTP. Please try again.\n"

def get_otp(user_id):
    stored_otp_data = otp_storage.get(user_id)
    return stored_otp_data

if __name__ == "__main__":
    otp = verify_otp(123456789, generate_otp(123456789))
    print(otp,generate_otp(123456789))