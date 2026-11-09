import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ML Inference — Middleware and Errors")


@app.middleware("http")
async def track_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Before routing: give this request an ID and start the timer.
    request.state.request_id = str(uuid4())
    started = perf_counter()

    response = await call_next(request)

    # On the way back: add the same headers to success and handled error responses.
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
    return response


# Added last, so CORS sits outside the timing middleware and can handle preflight.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
)


class PredictionInput(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    model_version: Literal["v1", "v2"] = "v1"


class ModelUnavailableError(Exception):
    """Signal that a recognized model version is temporarily offline."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Model {version} is unavailable")


@app.exception_handler(ModelUnavailableError)
async def handle_model_unavailable(
    request: Request, error: ModelUnavailableError
) -> JSONResponse:
    """Translate a model error into a consistent HTTP response."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "model_unavailable",
            "message": f"Sentiment model {error.version} is temporarily offline.",
            "request_id": request.state.request_id,
        },
    )


def predict_sentiment(text: str, version: str) -> str:
    """Stand in for a model service using a small keyword rule."""
    if version == "v2":
        raise ModelUnavailableError(version)

    words = set(re.findall(r"\b\w+\b", text.casefold()))
    score = len(words & {"love", "great", "helpful"}) - len(
        words & {"hate", "poor", "confusing"}
    )
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


@app.post("/predict")
def predict(data: PredictionInput) -> dict[str, str]:
    return {
        "label": predict_sentiment(data.text, data.model_version),
        "model_version": data.model_version,
    }
