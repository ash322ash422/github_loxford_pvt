"""Copy the latest prepared feature values into the SQLite online store."""
import pandas as pd
from common import ROOT, store


def materialize():
    frame = pd.read_parquet(ROOT / 'data/house_features.parquet')
    store().materialize(
        start_date=frame.event_timestamp.min().to_pydatetime(),
        end_date=(frame.event_timestamp.max() + pd.Timedelta(seconds=1)).to_pydatetime(),
    )


if __name__ == '__main__':
    materialize()
