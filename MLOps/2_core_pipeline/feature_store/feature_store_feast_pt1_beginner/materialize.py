"""Materialize means copy the latest features into the online store."""
import pandas as pd
from common import ROOT, store


def materialize():
    data = pd.read_parquet(ROOT / "data/housing.parquet")
    store().materialize(
        start_date=data.event_timestamp.min().to_pydatetime(),
        end_date=(data.event_timestamp.max() + pd.Timedelta(seconds=1)).to_pydatetime(),
    )


if __name__ == "__main__":
    materialize()
