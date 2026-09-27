FROM python:3.12


# specify Current Working Directory
WORKDIR /code

# copy requirements.txt from local to container
COPY ./requirements.txt /code/requirements.txt

# install all requirements in the container
RUN pip install --no-cache-dir --default-timeout=100 -r /code/requirements.txt

# copy dir app from local to container 
COPY . /code

# Expose port 8501 so other app can communicate with container
EXPOSE 8501

# Run following command to start app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]

