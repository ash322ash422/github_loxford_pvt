
# Browser Automation to Send WhatsApp Messages Using Python

# Install: pip install pywhatkit

# How It Works Under the Hood and Rules
# 1. Log in to WhatsApp Web First: Before running the script, open Google Chrome (or your default browser), 
#    go to ://whatsapp.com, and scan the QR code to ensure your personal account is fully logged in.
# 2. Keep the Computer Awake: The script controls your mouse and keyboard. Your computer must be powered on,
#    unlocked, and connected to the internet at the scheduled time.
# 3. The wait_time Delay: When the script runs, it opens a browser tab and waits for a few seconds 
#    (default is 15) to let WhatsApp Web fully load before it attempts to type. Do not click around or 
#    minimize the window while it is typing.


import pywhatkit as pwk

# Phone number must include the country code (e.g., +91 for India, +1 for US)
phone_number = "+919205950500" 
message = "Hello! This is an automated message sent using Python."

try:
    # This opens WhatsApp Web, types the message, waits 15 seconds, and presses Enter.
    # The 'True' parameter will close the browser tab 2 seconds after sending.
    pwk.sendwhatmsg_instantly(phone_number, message, wait_time=15, tab_close=True)
    print("Message automation triggered successfully!")

except Exception as e:
    print(f"An error occurred: {e}")
