
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np

# Load model
model = joblib.load("iris_model.pkl")

# Initialize FastAPI
app = FastAPI(title="Iris Classifier API")

# Define request schema
class IrisRequest(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Iris Classifier API"}

# Prediction endpoint
@app.post("/predict")
def predict(iris: IrisRequest):
    data = np.array([[iris.sepal_length, iris.sepal_width, iris.petal_length, iris.petal_width]])
    prediction = model.predict(data)[0]
    return {"prediction": int(prediction)}
