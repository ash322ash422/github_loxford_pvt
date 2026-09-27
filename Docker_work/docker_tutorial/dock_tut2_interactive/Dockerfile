
#NOTE The order is important
#Specify the base image. Following pulls the image from docker hub.
FROM python:3.8

#Add main.py to the container in  CWD
ADD main.py .

#Run  following cmd in  conntainer. 
RUN pip install requests beautifulsoup4

CMD ["python","./main.py"]

