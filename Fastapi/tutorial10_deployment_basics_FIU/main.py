import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Study Score Prediction API")

# Read deployment configuration when each server process imports the app.
APP_ENV = os.getenv("APP_ENV", "development")
MODEL_VERSION = os.getenv("MODEL_VERSION", "demo-v1")


class PredictionInput(BaseModel):
    hours_studied: float = Field(ge=0, le=24)


@app.get("/health")
def health() -> dict[str, str]:
    """Give the deployment platform a lightweight health endpoint."""
    return {"status": "ok", "environment": APP_ENV}


@app.post("/predict")
def predict(data: PredictionInput) -> dict[str, str | float]:
    """Use a toy formula so students can focus on deployment."""
    score = min(100.0, 35 + 6 * data.hours_studied)
    return {"predicted_score": round(score, 2), "model_version": MODEL_VERSION}
