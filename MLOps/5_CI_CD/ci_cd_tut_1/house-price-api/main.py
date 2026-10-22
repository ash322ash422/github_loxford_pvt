
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODEL_PATH = Path(__file__).with_name(
    "house_price_model.joblib"
)

app = FastAPI(title="House Price Prediction API")

model = None


@app.on_event("startup")
def load_model():
    global model

    if not MODEL_PATH.exists():
        raise RuntimeError(
            "Model file is missing. Run train.py first."
        )

    model = joblib.load(MODEL_PATH)


class HouseFeatures(BaseModel):
    area: float = Field(gt=0, le=100000)
    bedrooms: int = Field(ge=1, le=20)


@app.get("/")
def home():
    # return {"message": "House Price Prediction API"} # version 1
    return {"message": "House Price Prediction API - Version 2"}   # version 2


@app.get("/health")
def health():
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded"
        )

    return {"status": "healthy", "model_loaded": True}


@app.post("/predict")
def predict_price(house: HouseFeatures):
    features = np.array(
        [[house.area, house.bedrooms]],
        dtype=float
    )

    prediction = float(model.predict(features)[0])

    return {
        "area_sqft": house.area,
        "bedrooms": house.bedrooms,
        "predicted_price_lakhs": round(prediction, 2)
    }
