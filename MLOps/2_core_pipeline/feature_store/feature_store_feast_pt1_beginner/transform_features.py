"""Pipeline step 2: turn raw observations into prepared features for Feast."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent


def transform_features(raw_data):
    """Return a prepared copy, keeping the raw dataframe unchanged."""
    
    data = raw_data.copy()
    data["area_per_bedroom"] = data["area_sqft"] / data["bedrooms"]
    data["house_age_years"] = data["event_timestamp"].dt.year - data["year_built"]
    
    return data


def prepare_features():
    """Read the raw pipeline output and save the single prepared Feast source."""
    
    raw_data = pd.read_parquet(ROOT / "data/raw_housing.parquet")
    prepared_data = transform_features(raw_data)
    prepared_data.to_parquet(ROOT / "data/housing.parquet", index=False)
    print("Step 2: saved prepared features to data/housing.parquet")
    
    return prepared_data


if __name__ == "__main__":
    prepare_features()
