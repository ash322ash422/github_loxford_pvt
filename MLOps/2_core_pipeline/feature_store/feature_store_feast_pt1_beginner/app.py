"""Optional: the same prediction function inside a small FastAPI app."""
from fastapi import FastAPI, HTTPException
from predict import predict

app = FastAPI(title="Beginner Feast demo")


@app.get("/predict/{house_id}")
def predict_house(house_id: int):
    if not 1 <= house_id <= 100:
        raise HTTPException(status_code=404, detail="Use a house_id from 1 to 100.")
    try:
        return {"house_id": house_id, "predictions": predict(house_id)}
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
