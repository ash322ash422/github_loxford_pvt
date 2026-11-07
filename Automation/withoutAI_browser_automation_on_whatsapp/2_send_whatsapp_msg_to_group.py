# How It Works Under the Hood and Rules


import pywhatkit as pwk

# The group ID is the string at the end of the invite URL: ://chat.whatsapp.com...
group_id = "CtVFkZqTYMj2Lb5Ye7tZl1" 
message = "Hello! This is an automated message sent using Python."

try:
    # This opens WhatsApp Web, types the message, waits 15 seconds, and presses Enter.
    # The 'True' parameter will close the browser tab 2 seconds after sending.
    pwk.sendwhatmsg_to_group_instantly(
        group_id,
        "Hello everyone! Automated announcement.",
        wait_time=15, 
        tab_close=True
    )

    print("Message automation triggered successfully!")

except Exception as e:
    print(f"An error occurred: {e}")
