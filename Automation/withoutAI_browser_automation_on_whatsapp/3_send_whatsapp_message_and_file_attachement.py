# Note: This script uses the pywhatkit library to send a WhatsApp message with a file attachment.
# It olny send image not PDF.
import pywhatkit as pwk
import os

# 1. Recipient Details (Include country code)
phone_number = "+919205950500" # Replace with the recipient's phone number

# 2. File Path (Use an absolute path to avoid file-not-found errors)
# Example: "C"/Users/Name/Downloads/image.png"
file_path = os.path.abspath("JUNK_loxford_academy.png") 

try:
    # Opens WhatsApp web, attaches the file, waits 15 seconds for load time, and sends.
    # The final parameter 'True' automatically closes the browser tab 2 seconds after sending.
    pwk.sendwhats_image(
        receiver=phone_number,
        img_path=file_path,
        caption="Hello! Please find the attached document here.", # OPTIONAL: Add a caption for the file
        wait_time=15,
        tab_close=True
    )
    
    print("Automation triggered successfully. Keep your browser open...")

except Exception as e:
    print(f"An error occurred: {e}")
