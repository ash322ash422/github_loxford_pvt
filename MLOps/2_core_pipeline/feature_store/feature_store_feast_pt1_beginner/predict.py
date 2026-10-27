"""Predict with either model using just a house ID."""
import joblib
from common import ROOT, MODEL_FEATURES, store


def predict(house_id=1):
    fs = store()
    predictions = {}
    for name, columns in MODEL_FEATURES.items():
        feature_refs = [f"house_features:{column}" for column in columns]
        features = fs.get_online_features(
            features=feature_refs,
            entity_rows=[{"house_id": house_id}],
        ).to_df()[columns]
        if features.isna().any().any():
            raise ValueError("House features not found. Run the demo first and use IDs 1 to 100.")
        print(f"{name}: features retrieved from Feast:")
        print(features.to_string(index=False))
        model = joblib.load(ROOT / f"artifacts/{name}.joblib")
        predictions[name] = round(float(model.predict(features)[0]), 2)
        print(f"{name} prediction: ${predictions[name]:,.2f}")
    return predictions


if __name__ == "__main__":
    predict()
