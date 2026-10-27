"""Pipeline step 1: generate raw housing observations, without engineered features."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def get_data():
    rng = np.random.default_rng(42)
    houses = pd.DataFrame({
        "house_id": np.arange(1, 101, dtype=np.int64),
        "area_sqft": rng.integers(700, 3000, 100),
        "bedrooms": rng.integers(1, 5, 100),
        "year_built": rng.integers(1980, 2020, 100),
    })
    today = pd.Timestamp.now(tz="UTC").normalize()
    dates = pd.date_range(end=today, periods=24, freq="MS")
    snapshots = []
    for date in dates:
        frame = houses.copy()
        frame["event_timestamp"] = date
        # Make a synthetic target from raw attributes, with a premium for newer houses.
        # This simulates an observed price; it is not a model input feature.
        frame["sale_price"] = (
            frame.area_sqft * 180 + frame.bedrooms * 12000
            + (frame.year_built - 1980) * 1000
            + rng.normal(0, 10000, len(frame))
        ).round(2)
        snapshots.append(frame)

    raw_data = pd.concat(snapshots, ignore_index=True)
    (ROOT / "data").mkdir(exist_ok=True)
    raw_data.to_parquet(ROOT / "data/raw_housing.parquet", index=False)
    print(f"Step 1: saved {len(raw_data)} raw observations to data/raw_housing.parquet")
    return raw_data


if __name__ == "__main__":
    get_data()
