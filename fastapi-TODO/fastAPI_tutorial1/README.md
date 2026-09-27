# FastAPI tutorial
 Basic tutorial

1) Use "pip install fastapi" or "python -m pip install fastapi"

 PS C:\Users\hi\Desktop\projects\python_projects\fastAPI_tutorial1> pip install fastapi

2) Now install the server package:

 PS C:\Users\hi\Desktop\projects\python_projects\fastAPI_tutorial1> pip install "uvicorn[standard]"

 3) create main.py with necessary code and then run server:

PS C:\Users\hi\Desktop\projects\python_projects\fastAPI_tutorial1> uvicorn main:app --reload

4) Create main.py and model.py and use postman app to test the fastAPI. 

NOTE:You can also analyze/debug this app on URL 'http://127.0.0.1:8000/docs' on any regular browser.