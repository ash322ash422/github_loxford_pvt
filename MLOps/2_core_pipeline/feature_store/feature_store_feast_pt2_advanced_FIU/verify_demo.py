"""Meaningful checks: time travel, TTL, shared contracts, and real API calls."""
import pandas as pd
from fastapi.testclient import TestClient
from app import app
from common import ROOT, FEATURE_COLUMNS, SERVICES, store


def verify():
    fs = store()
    raw = pd.read_parquet(ROOT / 'data/market_features.parquet')
    dates = sorted(raw.event_timestamp.unique())
    old, latest = dates[60], dates[-1]
    queries = pd.DataFrame({'neighborhood_id': [1, 1, 1],
                            'event_timestamp': [old, latest, latest + pd.Timedelta(days=4)]})
    result = fs.get_historical_features(entity_df=queries, features=[
        'market_features:neighborhood_price_per_sqft_30d']).to_df().sort_values('event_timestamp')
    column = 'neighborhood_price_per_sqft_30d'
    expected = raw[(raw.neighborhood_id == 1) & (raw.event_timestamp == old)][column].iloc[0]
    assert abs(result.iloc[0][column] - expected) < 1e-8, 'Historical retrieval used wrong snapshot'
    expired = result[result.event_timestamp == latest + pd.Timedelta(days=4)]
    # Feast 0.67's file backend can omit a row when all candidates exceed TTL.
    assert expired.empty or expired[column].isna().all(), 'Expired feature was returned'
    assert len(result[result.event_timestamp == old]) == 1
    # Independently recompute the old rolling value from raw sales.
    sales = pd.read_parquet(ROOT / 'data/sales.parquet')
    houses = pd.read_parquet(ROOT / 'data/houses.parquet').set_index('house_id')
    window = sales[(sales.neighborhood_id == 1) & (sales.event_timestamp > old - pd.Timedelta(days=30)) & (sales.event_timestamp <= old)]
    assert abs((window.sale_price / window.house_id.map(houses.area_sqft)).mean() - expected) < 1e-8
    for name in SERVICES:
        historical = fs.get_historical_features(
            entity_df=pd.DataFrame({'house_id': [1], 'neighborhood_id': [int(houses.loc[1, 'neighborhood_id'])], 'event_timestamp': [latest]}),
            features=fs.get_feature_service(SERVICES[name]),
        ).to_df()
        with TestClient(app) as client:
            response = client.post('/predict', json={'house_id': 1, 'model': name})
            assert response.status_code == 200, response.text
            online = response.json()['features']
            for feature in FEATURE_COLUMNS:
                assert abs(online[feature] - historical.iloc[0][feature]) < 1e-8, feature
            assert client.post('/predict', json={'house_id': 999999}).status_code == 404
            assert client.post('/predict', json={'house_id': 1, 'model': 'unknown'}).status_code == 422
            print(name, response.json()['predicted_price'])
    print('PASS: historical snapshot, rolling window, TTL, online/offline parity, and both API models.')


if __name__ == '__main__':
    verify()
