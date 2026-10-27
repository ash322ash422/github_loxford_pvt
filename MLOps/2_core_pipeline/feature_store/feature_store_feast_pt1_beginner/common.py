"""Available features and the subset each model uses in training and prediction."""
from pathlib import Path
from feast import FeatureStore

ROOT = Path(__file__).resolve().parent
FEATURE_COLUMNS = ["area_sqft", "bedrooms", "area_per_bedroom", "house_age_years"]

# Feast uses the format feature_view_name:feature_name to locate a feature.
# prefix avoids ambiguity: different feature views could contain columns with the same name
FEATURE_REFS = [f"house_features:{name}" for name in FEATURE_COLUMNS]

MODEL_FEATURES = {
    "linear": ["area_sqft", "bedrooms"],  # Start with just two features.
    "forest": FEATURE_COLUMNS,  # Reuse all four prepared features.
}


def store():
    return FeatureStore(repo_path=str(ROOT / "feature_repo"))
