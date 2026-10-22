
import json
import joblib
import pandas as pd

from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

Path("models").mkdir(exist_ok=True)

df = pd.read_csv("data/houses.csv")

X = df[
    ["area_sqft", "bedrooms", "age_years", "location_score"]
]
y = df["price_lakh"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

model = LinearRegression()
model.fit(X_train, y_train)

predictions = model.predict(X_test)

metrics = {
    "mae_lakh": round(float(
        mean_absolute_error(y_test, predictions)
    ), 3),
    "r2": round(float(
        r2_score(y_test, predictions)
    ), 3)
}

joblib.dump(model, "models/house_price_model.joblib")

with open("metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

print("Model evaluation:")
print(json.dumps(metrics, indent=2))
