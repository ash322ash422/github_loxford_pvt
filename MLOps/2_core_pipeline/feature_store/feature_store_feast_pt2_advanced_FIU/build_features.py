"""The ONE shared batch transformation, used before both training and serving."""
import numpy as np
import pandas as pd
from generate_data import ROOT


def build():
    homes = pd.read_parquet(ROOT / 'data/houses.parquet')
    sales = pd.read_parquet(ROOT / 'data/sales.parquet')
    dates = pd.date_range(sales.event_timestamp.min(), sales.event_timestamp.max(), freq='D')
    house_frames = []
    market_frames = []
    for date in dates:
        frame = homes[['house_id', 'area_sqft', 'bedrooms']].copy()
        frame['log_area'] = np.log1p(homes.area_sqft)
        frame['area_per_bedroom'] = homes.area_sqft / homes.bedrooms
        frame['house_age_years'] = date.year - homes.year_built
        frame['event_timestamp'] = date
        house_frames.append(frame)
        
        # Trailing 30 days: (date - 30 days, date]. All inputs are known at date.
        past = sales[(sales.event_timestamp > date - pd.Timedelta(days=30)) & (sales.event_timestamp <= date)].copy()
        past['price_per_sqft'] = past.sale_price / past.house_id.map(homes.set_index('house_id').area_sqft)
        market = past.groupby('neighborhood_id').agg(
            neighborhood_price_per_sqft_30d=('price_per_sqft', 'mean'),
            neighborhood_sales_count_30d=('sale_price', 'count'),
        ).reset_index()
        market['event_timestamp'] = date
        market_frames.append(market)

    pd.concat(house_frames).to_parquet(ROOT / 'data/house_features.parquet', index=False)
    pd.concat(market_frames).to_parquet(ROOT / 'data/market_features.parquet', index=False)
    
    print('Prepared shared house features and trailing 30-day neighborhood features.')


if __name__ == '__main__':
    build()
