"""Small instructor check; not required to follow the lesson."""
import pandas as pd
import joblib
from common import ROOT, FEATURE_COLUMNS, FEATURE_REFS, MODEL_FEATURES, store
from predict import predict
from transform_features import transform_features


def verify():
    fs = store()
    data = pd.read_parquet(ROOT / "data/housing.parquet")
    raw = pd.read_parquet(ROOT / "data/raw_housing.parquet")
    assert "area_per_bedroom" not in raw and "house_age_years" not in raw
    pd.testing.assert_frame_equal(transform_features(raw), data)
    assert "area_per_bedroom" not in raw, "Transformation should leave raw inputs unchanged"
    assert len(FEATURE_COLUMNS) == 4
    assert len(fs.list_feature_views()) == 1
    house = data[data.house_id == 1].sort_values("event_timestamp")
    # Query halfway through two different months, rather than at snapshot times.
    expected = house.iloc[[0, -1]].reset_index(drop=True)
    queries = expected[["house_id", "event_timestamp"]].copy()
    queries["event_timestamp"] += pd.Timedelta(days=10)
    historical = fs.get_historical_features(entity_df=queries, features=FEATURE_REFS).to_df().sort_values("event_timestamp")
    pd.testing.assert_frame_equal(historical[FEATURE_COLUMNS].reset_index(drop=True), expected[FEATURE_COLUMNS], check_dtype=False)
    assert historical.house_age_years.iloc[0] < historical.house_age_years.iloc[-1]
    online = fs.get_online_features(features=FEATURE_REFS, entity_rows=[{"house_id": 1}]).to_df()
    pd.testing.assert_frame_equal(online[FEATURE_COLUMNS].reset_index(drop=True), house.iloc[[-1]][FEATURE_COLUMNS].reset_index(drop=True), check_dtype=False)
    labels = data[["house_id", "event_timestamp", "sale_price"]].head(3)
    for name, columns in MODEL_FEATURES.items():
        subset = fs.get_historical_features(
            entity_df=labels,
            features=[f"house_features:{column}" for column in columns],
        ).to_df()
        assert set(subset.columns) == set(labels.columns) | set(columns)
        model = joblib.load(ROOT / f"artifacts/{name}.joblib")
        assert list(model.feature_names_in_) == columns
    assert len(predict(1)) == 2
    print("PASS: pipeline, historical features, model-specific subsets, online values, both predictions.")


if __name__ == "__main__":
    verify()
