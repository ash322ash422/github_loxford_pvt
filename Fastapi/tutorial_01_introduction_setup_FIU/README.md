# Lesson 1 — Introduction to FastAPI and setup

**Class time** 20–25 minutes. Students will run a Python API, make their first GET request, and explore the documentation generated from their code.

## 1. What is FastAPI?

FastAPI is a Python web framework for building APIs. A client, such as a browser, Postman, or another Python program, sends an HTTP request. FastAPI routes the request to a Python function and turns the result into an HTTP response. In this lesson, the result is a dictionary that FastAPI sends as JSON.

FastAPI can use Python type hints to validate inputs and describe them in an OpenAPI schema. That schema powers the interactive documentation students will open today.

| Framework | When you might choose it |
| --- | --- |
| **FastAPI** | You're building a JSON API, such as a model prediction endpoint, and want validation and API documentation from type hints. |
| **Flask** | You want a small, flexible web framework and prefer to choose how to add API validation, documentation, or database tools. |
| **Django** | You're building a larger web application and want integrated features such as a database ORM, authentication, and an admin interface. |

For this course, FastAPI gives students a short path from a Python function to a documented JSON endpoint.

## 2. Explain ASGI and Uvicorn

**ASGI** stands for **Asynchronous Server Gateway Interface**. It's the standard interface between an ASGI server and a Python application. It supports asynchronous communication, including HTTP and WebSockets. The starter route uses plain `def`, so students can focus on routing before learning `async def`.

**Uvicorn** listens for incoming requests and passes them to the FastAPI app through ASGI. **FastAPI** decides which route to call and builds the response. When students visit `/`, the browser talks to Uvicorn, and FastAPI calls `read_root()`.

## 3. Install and run on Windows

Open PowerShell in this lesson folder with Python 3.11 or later. If `python --version` shows the wrong interpreter, select the intended Python version before creating the virtual environment.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The requirements file installs FastAPI and Uvicorn together. In `main:app`, `main` is the module `main.py`, and `app` is the object created inside it. `--reload` restarts the app when you save code changes during development. Keep this terminal open. Press Ctrl+C when you're ready to stop the server.

## 4. Walk through the first app

1. `from fastapi import FastAPI` imports the framework's application class.
2. `app = FastAPI(...)` creates the application. The title appears in the generated docs.
3. `@app.get("/")` registers a route for the HTTP method `GET` and path `/`.
4. `read_root()` returns a Python dictionary. Visit [the root endpoint](http://127.0.0.1:8000/) and expect **200 OK** with this JSON.

```json
{"message": "Hello, FastAPI!"}
```

## 5. Explore the automatic documentation

| Address | What to do |
| --- | --- |
| [Swagger UI](http://127.0.0.1:8000/docs) | Expand `GET /`, click **Try it out**, then **Execute**. Find the request URL, status code, and response body. |
| [ReDoc](http://127.0.0.1:8000/redoc) | Find `GET /` in the reference and read its response details. |
| [OpenAPI JSON](http://127.0.0.1:8000/openapi.json) | Find `paths` and look for `/` and its `get` operation. This machine-readable description supplies both documentation views. |

## Student exercise

Add a second route, `GET /health`, that returns `{"status": "ok"}`. Save `main.py`, then refresh Swagger UI and execute the new route. Ask students to identify the HTTP method, path, status code, and JSON body.

[FastAPI first steps](https://fastapi.tiangolo.com/tutorial/first-steps/) · [ASGI introduction](https://asgi.readthedocs.io/en/latest/introduction.html) · [Flask design](https://flask.palletsprojects.com/en/stable/design/) · [Django overview](https://docs.djangoproject.com/en/stable/intro/overview/)
