"""Production-style serving: entity keys -> Feast -> saved model -> price."""
from contextlib import asynccontextmanager
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from common import ROOT, SERVICES, store


@asynccontextmanager
async def lifespan(app):
    app.state.fs = store()
    app.state.models = {name: joblib.load(ROOT / f'artifacts/{name}.joblib') for name in SERVICES}
    app.state.houses = pd.read_parquet(ROOT / 'data/houses.parquet').set_index('house_id')
    yield


app = FastAPI(title='Shared housing features: two price models', lifespan=lifespan)


class PredictionRequest(BaseModel):
    house_id: int = Field(gt=0)
    model: Literal['linear', 'forest'] = 'forest'


@app.post('/predict')
def predict(request: PredictionRequest):
    if request.house_id not in app.state.houses.index:
        raise HTTPException(404, 'Unknown house_id; generate and materialize its features first.')
    neighborhood = int(app.state.houses.loc[request.house_id, 'neighborhood_id'])
    bundle = app.state.models[request.model]
    features = app.state.fs.get_online_features(
        features=app.state.fs.get_feature_service(bundle['service']),
        entity_rows=[{'house_id': request.house_id, 'neighborhood_id': neighborhood}],
    ).to_df()
    if features[bundle['columns']].isna().any().any():
        raise HTTPException(503, 'Features unavailable. Run materialize.py.')
    price = bundle['model'].predict(features[bundle['columns']])[0]
    return {'house_id': request.house_id, 'model': request.model,
            'predicted_price': round(float(price), 2),
            'features': features[bundle['columns']].iloc[0].to_dict()}
