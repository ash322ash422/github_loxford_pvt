"""Step 1: generate a small clean table and copies with deliberate mistakes."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def get_data():
    rng = np.random.default_rng(42)
    
    data = pd.DataFrame({
        "house_id": np.arange(1, 101, dtype=np.int64),
        "area_sqft": rng.integers(700, 3000, 100).astype(float),
        "bedrooms": rng.integers(1, 6, 100),
        "year_built": rng.integers(1980, 2020, 100),
    })
    data["sale_price"] = (
        data.area_sqft * 180 + data.bedrooms * 12000
        + (data.year_built - 1980) * 1000 + rng.normal(0, 8000, len(data))
    ).round(2)

    # Keep the original intact. Each copy represents a new incoming delivery.
    dirty = data.copy()
    dirty.loc[[0, 1], "area_sqft"] = np.nan  # Missing values.
    dirty.loc[2, "sale_price"] = -50000      # Impossible price.
    dirty.loc[3, "bedrooms"] = 0             # Invalid room count.
    dirty.loc[4, "house_id"] = dirty.loc[5, "house_id"]  # Duplicate key.

    # A producer changed the schema.
    bad_schema = data.drop(columns="bedrooms")  

    # Few columns have wrong data type
    bad_type = data.copy()
    bad_type["sale_price"] = bad_type.sale_price.astype(object)
    bad_type.loc[0, "sale_price"] = "unknown"  # Text in a numeric column.

    (ROOT / "data").mkdir(exist_ok=True)
    for name, frame in {"clean": data, "dirty": dirty,
                        "bad_schema": bad_schema, "bad_type": bad_type}.items():
        frame.to_csv(ROOT / f"data/houses_{name}.csv", index=False)
        
    print("Created four small CSV examples in data/ (100 rows each).")
    return data, dirty


if __name__ == "__main__":
    get_data()
