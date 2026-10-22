
# Lets generate a synthetic dataset of house prices based on 
# some features like area, number of bedrooms, age of the house, and location score.

import random
import pandas as pd
from pathlib import Path

random.seed(42)

rows = []

for _ in range(60):
    area = random.randint(600, 3000)
    bedrooms = max(1, min(5, round(area / 550)))
    age = random.randint(0, 35)
    location_score = random.randint(1, 10)

    # Artificial pricing rule, in INR lakh
    price = (
        12
        + area * 0.045
        + bedrooms * 4.5
        - age * 0.35
        + location_score * 3.2
        + random.uniform(-5, 5)
    )

    rows.append({
        "area_sqft": area,
        "bedrooms": bedrooms,
        "age_years": age,
        "location_score": location_score,
        "price_lakh": round(price, 2)
    })

Path("data").mkdir(exist_ok=True)

df = pd.DataFrame(rows)
df.to_csv("data/houses.csv", index=False)

print(df.head())
print("Dataset shape:", df.shape)
