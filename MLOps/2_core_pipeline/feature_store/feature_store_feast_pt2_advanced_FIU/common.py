"""Shared retrieval contract and deterministic model input ordering."""
from pathlib import Path
from feast import FeatureStore

ROOT = Path(__file__).resolve().parent
FEATURE_COLUMNS = ['area_sqft', 'bedrooms', 'log_area', 'area_per_bedroom',
                   'house_age_years', 'neighborhood_price_per_sqft_30d',
                   'neighborhood_sales_count_30d']
SERVICES = {'linear': 'linear_price_v1', 'forest': 'forest_price_v1'}


def store():
    return FeatureStore(repo_path=str(ROOT / 'feature_repo'))
