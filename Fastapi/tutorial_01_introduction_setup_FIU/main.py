from fastapi import FastAPI

app = FastAPI(title="My First FastAPI App")


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a JSON greeting for GET requests to the root path."""
    return {"message": "Hello, FastAPI!"}
