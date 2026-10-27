"""Step 3: feature engineering, after the input has passed validation."""


def transform_data(data):
    prepared = data.copy()
    prepared["area_per_bedroom"] = prepared["area_sqft"] / prepared["bedrooms"]
    return prepared
