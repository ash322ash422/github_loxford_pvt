"""Train two models, each requesting its own feature subset from Feast."""
import json
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from common import ROOT, MODEL_FEATURES, store


def train():
    data = pd.read_parquet(ROOT / "data/housing.parquet")

    # Start with identifiers, prediction dates, and labels. Get inputs FROM Feast.
    labels = data[["house_id", "event_timestamp", "sale_price"]]
    # Use earlier months for training and the final four months for testing.
    dates = sorted(labels.event_timestamp.unique())
    fs = store()

    # Different subsets from the same feature view. No new feature engineering.
    models = {
        "linear": LinearRegression(),
        "forest": RandomForestRegressor(n_estimators=50, random_state=42),
    }
    (ROOT / "artifacts").mkdir(exist_ok=True)
    metrics = {}
    for name, model in models.items():
        columns = MODEL_FEATURES[name]
        feature_refs = [f"house_features:{column}" for column in columns]
        training_data = fs.get_historical_features(
            entity_df=labels,
            features=feature_refs,
        ).to_df()
        assert len(training_data) == len(labels), "Some feature rows are missing."
        assert not training_data[columns].isna().any().any()

        is_train = training_data.event_timestamp < dates[-4]
        X_train = training_data.loc[is_train, columns]
        y_train = training_data.loc[is_train, "sale_price"]
        X_test = training_data.loc[~is_train, columns]
        y_test = training_data.loc[~is_train, "sale_price"]
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        metrics[name] = round(float(mean_absolute_error(y_test, predictions)), 2)
        joblib.dump(model, ROOT / f"artifacts/{name}.joblib")
        print(f"{name} uses {len(columns)} features: {columns}")
        print(f"  Test MAE = ${metrics[name]:,.2f}")

    (ROOT / "artifacts/metrics.json").write_text(json.dumps(metrics, indent=2))
    print("Different feature subsets, one shared Feast feature view.")
    return training_data


if __name__ == "__main__":
    train()
