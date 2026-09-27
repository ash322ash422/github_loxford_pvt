#NOTE The order is important
#Specify the base image. Following pulls the image from docker hub.
FROM python:3.12.3-slim-bullseye

RUN pip install --upgrade pip

#following helpful; for debuging.Errors are not lost.
ENV PYTHONUNBUFFERED=1

##Lets create a WD in container. This would also be CWD.
WORKDIR /app

#copy requirements.txt from local m/c to container WORKDIR
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

#Copy all from CWD in local m/c to WORKDIR in container
COPY . .

#I can enter more commands here
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

