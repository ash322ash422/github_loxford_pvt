FROM python:3.12

# specify Current Working Directory
WORKDIR /code

# copy requirements.txt from local to container
COPY ./requirements.txt /code/requirements.txt

# install all requirements in the container
RUN pip install --no-cache-dir --default-timeout=100 -r /code/requirements.txt

# copy dir app from local to container 
COPY ./app /code/app

# Expose port 8000 so other app can communicate with container
EXPOSE 8000

# Run following command to start uvicorn server
CMD ["uvicorn", "app.server_app:app", "--host", "0.0.0.0", "--port", "8000"]

