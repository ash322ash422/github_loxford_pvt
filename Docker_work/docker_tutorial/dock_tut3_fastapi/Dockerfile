FROM python:3.8

#Lets create a WD in container. This would also be CWD.
WORKDIR /fastapi-app

#copy the requirements.txt from local m/c to the containers WORKDIR 
COPY requirements.txt .

#Install the dependencies in the container
RUN pip install -r requirements.txt

#copy app from local  m/c to dir container_dir_for_app  
COPY ./app ./container_dir_for_app

#Specify the entry point
CMD ["python","./container_dir_for_app/main.py"]