"""Generate reproducible houses, historical sales, and future prediction labels."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def generate(seed=42, houses=300, days=180):
    rng = np.random.default_rng(seed)
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    end = pd.Timestamp.now(tz='UTC').normalize()
    dates = pd.date_range(end=end, periods=days, freq='D')
    homes = pd.DataFrame({
        'house_id': np.arange(1, houses + 1, dtype=np.int64),
        'neighborhood_id': rng.integers(1, 7, houses),
        'area_sqft': rng.integers(650, 3500, houses),
        'bedrooms': rng.integers(1, 6, houses),
        'year_built': rng.integers(1970, 2020, houses),
    })

    records = []
    for day_number, date in enumerate(dates):
        # Each sale is known only at its recorded timestamp (no delayed ingestion).
        for row in homes.sample(35, random_state=seed + day_number).itertuples(index=False):
            unit_price = 125 + 22 * row.neighborhood_id + 0.16 * day_number
            price = row.area_sqft * unit_price + row.bedrooms * 9000 - (date.year - row.year_built) * 500
            records.append((row.house_id, row.neighborhood_id, date, max(50000, price + rng.normal(0, 18000))))

    sales = pd.DataFrame(records, columns=['house_id', 'neighborhood_id', 'event_timestamp', 'sale_price'])

    # Features at midnight predict sales on the NEXT day. Targets never enter Feast.
    labels = sales.rename(columns={'event_timestamp': 'sale_timestamp'})
    labels['event_timestamp'] = labels['sale_timestamp'] - pd.Timedelta(days=1)
    labels = labels[labels.event_timestamp >= dates[31]].reset_index(drop=True)
    homes.to_parquet(out / 'houses.parquet', index=False)
    sales.to_parquet(out / 'sales.parquet', index=False)
    labels.to_parquet(out / 'labels.parquet', index=False)
    
    print(f'Generated {len(homes)} houses, {len(sales)} sales, {len(labels)} labels in {out}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    generate(seed=args.seed)
