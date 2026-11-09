# fastAPI_tutorial_Authenticate1
 
 NOTE:For this project I am using  python3.9 

STEPS FOR CREATING VIRTUAL ENV IN VS CODE ON WINDOWS:

*) Open a new folder in VS Code.

*) Click 'view'->'command palette' -> 'Python:select interpreter' -> '+Create Virtual Environment'

*) Now you can select your python interpreter here. You should see your env on bottom RHS.

*) To install packages use : 'python -m pip install <package_name>'. This will automatically select your python interpreter.
or type 'python -m pip install -r requirements.txt'
Package installed are : fastapi, "uvicorn[standard]", python-multipart, "python-jose[cryptography]", "passlib[bcrypt]"

1) Create 1_main.py and 1_test_server.py and then 'uvicorn.exe 1_main:app --reload'
   
2) Create 2_main.py and 2_test_server.py and then 'uvicorn.exe 2_main:app --reload'

 NOTE:You can analyze/debug this app on URL 'http://127.0.0.1:8000/docs'

 3) Need to install openssl: Goto "https://wiki.openssl.org/index.php/Binaries" -> click https://www.firedaemon.com/get-openssl and download from here.