#NOTE The order is important
#Specify the base image. Following pulls the image from docker hub.
FROM python:3.9

RUN pip install mysql-connector-python

WORKDIR /usr/app/src

COPY hello_world.py ./