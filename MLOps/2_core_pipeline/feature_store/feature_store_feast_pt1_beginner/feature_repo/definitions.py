"""One entity, one file source, one feature view."""

from datetime import timedelta
from pathlib import Path
from feast import Entity, FeatureView, Field, FileSource, ValueType
from feast.types import Float64, Int64

# Entity: the thing whose features we want to retrieve.
house = Entity(name="house",
               join_keys=["house_id"],
               value_type=ValueType.INT64
)

# Source: the ONE prepared data file Feast reads.
housing_source = FileSource(
    path=str(Path(__file__).resolve().parents[1] / "data/housing.parquet"),
    timestamp_field="event_timestamp",
)

# Feature view: a named group of reusable features.
house_features = FeatureView(
    name="house_features",
    entities=[house],
    ttl=timedelta(days=40),  # Allow a monthly snapshot up to 40 days old.
    schema=[
        Field(name="area_sqft", dtype=Int64),
        Field(name="bedrooms", dtype=Int64),
        Field(name="area_per_bedroom", dtype=Float64),
        Field(name="house_age_years", dtype=Int64),
    ],

    source=housing_source,
    online=True,
)
