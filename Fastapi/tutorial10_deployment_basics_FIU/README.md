# FastAPI classroom project — Deployment basics

**Class time** 35–45 minutes. Run a small prediction API on Windows, change its configuration without editing Python, then package it into a Linux container. The prediction uses a toy formula so the class can focus on deployment.

## 1. Run locally with Uvicorn

Open PowerShell in this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

`main:app` tells the server to load the `app` object from `main.py`. Uvicorn is an ASGI server. It listens for HTTP requests and passes them to FastAPI. `--reload` watches for code edits during development.

| Endpoint | Try it |
| --- | --- |
| [GET /health](http://127.0.0.1:8000/health) | Expect `{"status":"ok","environment":"development"}` with the default configuration. |
| [POST /predict in Swagger UI](http://127.0.0.1:8000/docs) | Send `{"hours_studied": 5}`. Expect `{"predicted_score":65.0,"model_version":"demo-v1"}`. |

## 2. Change settings with environment variables

An environment variable is a named value supplied to a process by its shell, container, or cloud platform. Here Python reads `APP_ENV` and `MODEL_VERSION` when the application process imports `main.py`.

Stop Uvicorn with Ctrl+C, then run these commands in the same PowerShell window.

```powershell
$env:APP_ENV = 'staging'
$env:MODEL_VERSION = 'demo-v2'
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Repeat the requests. `/health` now shows `staging`, and `/predict` reports `demo-v2`. The version is a label in this demo. The score still comes from the same formula. This illustrates how different deployments can run identical code with different settings. Keep real credentials in the cloud platform's secret store.

## 3. Package and run the same app with Docker

The **Dockerfile** is the build recipe. An **image** packages Python, dependencies, and the application. A **container** is a running instance of that image.

With Docker Desktop running in Linux container mode, use a second PowerShell window in this folder.

```powershell
docker build -t fastapi-study-score:1.0 .
docker run --rm --name study-score -p 127.0.0.1:8001:8000 -e APP_ENV=container -e MODEL_VERSION=demo-v3 fastapi-study-score:1.0
```

Open [container health](http://127.0.0.1:8001/health) or [container Swagger UI](http://127.0.0.1:8001/docs). Docker forwards port `8001` on your computer to port `8000` inside the container. The server listens on `0.0.0.0` inside the container so this forwarding can reach it. The Dockerfile starts Uvicorn without reload. Press Ctrl+C to stop the demo container.

## 4. Try Gunicorn with the same Docker image

Gunicorn manages worker processes. The image installs Gunicorn on Linux, so Windows students can run it inside Docker. This example uses Gunicorn's built-in ASGI worker and starts two processes.

```powershell
docker run --rm --name study-score-gunicorn -p 127.0.0.1:8001:8000 -e APP_ENV=container fastapi-study-score:1.0 gunicorn main:app --worker-class asgi --workers 2 --bind 0.0.0.0:8000
```

The command after the image name replaces the Dockerfile's default Uvicorn command. Call `/health` again and identify the two workers in the startup output. In a real ML service, each worker may load its own copy of the model, so measure memory before increasing the worker count.

## 5. Explain the path to AWS

Use **AWS Elastic Beanstalk's Docker platform** as the classroom example. This is an overview.

1. **Verify locally.** Build the Docker image and confirm both endpoints work.
2. **Deliver the application.** Package the Dockerfile and source files at the root of the deployment bundle. Elastic Beanstalk can build the image from that Dockerfile. Teams that publish prebuilt images can use a registry such as Amazon ECR and reference the image in the deployment configuration.
3. **Configure the environment.** Set application settings such as `APP_ENV=production` and `MODEL_VERSION=demo-v1`. The container listens on port `8000`. In a load-balanced environment, configure `/health` as the application health-check path.
4. **Verify the deployment.** Call `/health` and `/predict` using the environment URL. Check deployment events and server logs if either request fails.

## Student exercise

Run a second container from the same image on host port `8002` with `MODEL_VERSION=demo-v4`. Send the same prediction to both running containers and explain why the score matches while the version label differs.

[FastAPI in containers](https://fastapi.tiangolo.com/deployment/docker/) · [Gunicorn ASGI worker](https://gunicorn.org/asgi/) · [Elastic Beanstalk Docker platform](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/docker.html)
