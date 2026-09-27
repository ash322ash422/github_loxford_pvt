# fastAPI_tutorial2
 
 NOTE:For this project I am using  python3.12. 

STEPS FOR CREATING VIRTUAL ENV IN VS CODE ON WINDOWS:

*) Open a new folder in VS Code.

*) Click 'view'->'command palette' -> 'Python:select interpreter' -> '+Create Virtual Environment' and choose 'Venv'

*) Now you can select your python interpreter here. You should see your env on bottom RHS.

*) To install packages use : 'python -m pip install <package_name>'. This will automatically select your python interpreter.

I used 'python -m pip install fastapi' , 'python -m pip install "uvicorn[stantdard]"' and 'python -m pip install requests'

1) Create 1_main.py and 1_test_server.py and then 'uvicorn.exe 1_main:app --reload'
   
2) Create 2_main.py and 2_test_server.py and then 'uvicorn.exe 2_main:app --reload'

 NOTE:You can analyze/debug this app on URL 'http://127.0.0.1:8000/docs'