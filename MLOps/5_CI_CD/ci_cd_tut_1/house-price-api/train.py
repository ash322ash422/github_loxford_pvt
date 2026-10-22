
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


MODEL_PATH = Path("house_price_model.joblib")


def train_model():
    rng = np.random.default_rng(42)

    # Synthetic house data: area in square feet
    # and bedrooms; price is in lakh rupees.
    area = rng.integers(500, 3001, size=200)
    bedrooms = rng.integers(1, 6, size=200)

    noise = rng.normal(0, 2, size=200)
    price = 20 + 0.05 * area + 5 * bedrooms + noise

    X = np.column_stack([area, bedrooms])
    y = price

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = make_pipeline(
        StandardScaler(),
        LinearRegression()
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)

    # Example ML quality gate.
    if mae > 5:
        raise ValueError(
            f"Model quality check failed: MAE={mae:.2f}"
        )

    joblib.dump(model, MODEL_PATH)

    print(f"Model saved to {MODEL_PATH}")
    print(f"Validation MAE: {mae:.2f} lakh rupees")

    return model, mae


if __name__ == "__main__":
    train_model()
