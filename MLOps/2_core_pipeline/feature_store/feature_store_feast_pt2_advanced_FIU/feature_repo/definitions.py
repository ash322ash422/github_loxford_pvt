"""Versioned, reusable feature contracts; no target columns here."""
from datetime import timedelta
from pathlib import Path
from feast import Entity, FeatureService, FeatureView, Field, FileSource, ValueType
from feast.types import Float64, Int64

DATA = Path(__file__).resolve().parents[1] / 'data'
house = Entity(name='house', join_keys=['house_id'], value_type=ValueType.INT64)
neighborhood = Entity(name='neighborhood', join_keys=['neighborhood_id'], value_type=ValueType.INT64)
house_features = FeatureView(
    name='house_features', entities=[house], ttl=timedelta(days=2),
    schema=[Field(name=n, dtype=t) for n, t in [
        ('area_sqft', Int64), ('bedrooms', Int64), ('log_area', Float64),
        ('area_per_bedroom', Float64), ('house_age_years', Int64)]],
    source=FileSource(path=str(DATA / 'house_features.parquet'), timestamp_field='event_timestamp'),
)
market_features = FeatureView(
    name='market_features', entities=[neighborhood], ttl=timedelta(days=2),
    schema=[Field(name='neighborhood_price_per_sqft_30d', dtype=Float64),
            Field(name='neighborhood_sales_count_30d', dtype=Int64)],
    source=FileSource(path=str(DATA / 'market_features.parquet'), timestamp_field='event_timestamp'),
)
# Separate model contracts reuse the SAME views; both intentionally use all features.
linear_price_v1 = FeatureService(name='linear_price_v1', features=[house_features, market_features])
forest_price_v1 = FeatureService(name='forest_price_v1', features=[house_features, market_features])
