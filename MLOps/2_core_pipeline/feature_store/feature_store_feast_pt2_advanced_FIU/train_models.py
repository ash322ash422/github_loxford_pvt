"""Two algorithms independently retrieve the same reusable Feast features."""
import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from common import ROOT, FEATURE_COLUMNS, SERVICES, store


def train():
    fs = store()
    labels = pd.read_parquet(ROOT / 'data/labels.parquet')
    cutoff = sorted(labels.event_timestamp.unique())[int(labels.event_timestamp.nunique() * .8)]
    models = {'linear': make_pipeline(StandardScaler(), Ridge(alpha=10)),
              'forest': RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)}
    out = ROOT / 'artifacts'
    out.mkdir(exist_ok=True)
    metrics = {}
    baseline = None
    for name, model in models.items():
        data = fs.get_historical_features(
            entity_df=labels,
            features=fs.get_feature_service(SERVICES[name]),
        ).to_df().sort_values(['event_timestamp', 'house_id']).reset_index(drop=True)
        assert len(data) == len(labels), 'Historical retrieval lost label rows; check source coverage and TTL'
        assert not data[FEATURE_COLUMNS].isna().any().any(), 'Missing/expired historical features'
        if baseline is None:
            baseline = data[FEATURE_COLUMNS].copy()
        else:
            pd.testing.assert_frame_equal(baseline, data[FEATURE_COLUMNS])
        train_mask = data.event_timestamp < cutoff
        model.fit(data.loc[train_mask, FEATURE_COLUMNS], data.loc[train_mask, 'sale_price'])
        predicted = model.predict(data.loc[~train_mask, FEATURE_COLUMNS])
        metrics[name] = {'mae': float(mean_absolute_error(data.loc[~train_mask, 'sale_price'], predicted)),
                         'rmse': float(root_mean_squared_error(data.loc[~train_mask, 'sale_price'], predicted)),
                         'train_rows': int(train_mask.sum()), 'test_rows': int((~train_mask).sum())}
        joblib.dump({'model': model, 'columns': FEATURE_COLUMNS, 'service': SERVICES[name]}, out / f'{name}.joblib')
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2))
    print('Verified: both models trained from identical Feast feature values; test dates follow training dates.')


if __name__ == '__main__':
    train()
