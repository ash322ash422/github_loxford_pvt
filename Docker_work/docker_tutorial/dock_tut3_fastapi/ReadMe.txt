1) Install fastapi: 
..\docker_tutorial\dock_tut3_fastapi> pip install fastapi

2) Create dock_tut3_fastapi/app/main.py file

3) Run the main.py file:
..dock_tut3_fastapi\app> python.exe .\main.py

4) The URL localhost:8000 , localhost:8000//items/5?q=somequery and PUT URL works.
So, the Server is working. Good

5) Now all dependeancies in requirements.txt file.
..\docker_tutorial\dock_tut3_fastapi> pip freeze > requirements.txt

5) Now create Dockerfile

6) Build the docker container:
..\docker_tutorial\dock_tut3_fastapi> docker build -t python-fastapi .

7) Run the container:
..\docker_tutorial\dock_tut3_fastapi> docker run -p 8000:8000 python-fastapi
