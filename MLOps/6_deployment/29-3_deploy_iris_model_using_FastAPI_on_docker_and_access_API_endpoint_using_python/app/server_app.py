from fastapi import FastAPI
import joblib
import numpy as np
from sklearn.datasets import load_iris

model = joblib.load('app/iris_model.pkl')

app = FastAPI()

@app.get('/')
def read_root():
    return {'message': 'Welcome to Iris model API'}

@app.post('/predict')
def predict(data: dict):
    features = np.array(data['features']).reshape(1, -1)
    prediction = model.predict(features)
    class_name = load_iris().target_names[prediction[0]]
    return {'predicted_class': class_name}

