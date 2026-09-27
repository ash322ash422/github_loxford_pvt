# Deploy ML model on Docker and use FastAPI to access its API endpoint

##### Prerequisite: Install docker
To install goto: https://docs.docker.com/engine/install/

### step 1: Train and save the ML model
See the code in **train_and_save_model.py**

### step 2: create fastAPI server

See the code **server_app.py**

### step 3: create requirements.txt file

See the file **requirements.txt**

### step 4: create Docker file
See the **Docker** file

##### step a: Start docker engine
Start the docker engine by simply running the **Docker Desktop**: Start -> Docker Desktop

##### step b: Build docker image
Run following command in same dir which contains Dockerfile:
```
docker build -t image_ml_model .
```
This would pull the image from docker hub. This could take **4 - 10 minutes**.

##### step c: Run container
```
docker run --name container_ml_model -p 8000:8000 image_ml_model
```

- NOTE: If you make a mistake, then delete the container_ml_model 
```
docker rm -f <container_id_name>
```
and redo above steps

### step 5: Goto URL http://127.0.0.1:8000/
You should see a simple Welcome message

### step 6: Access the API endpoint via python program
Run the file **client_to_access_API_endpoint.py** in a dedicated terminal


