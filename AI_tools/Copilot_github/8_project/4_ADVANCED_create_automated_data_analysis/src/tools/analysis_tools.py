from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def analyze_dataset(df: pd.DataFrame) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    numeric = df.select_dtypes(include=np.number)
    categorical = df.select_dtypes(exclude=np.number)
    stats = numeric.describe().round(4).to_dict() if not numeric.empty else {}
    correlations = (
        numeric.corr().round(4).replace({np.nan: None}).to_dict()
        if len(numeric.columns) > 1
        else {}
    )
    groups: dict[str, Any] = {}
    for column in categorical.columns:
        if not numeric.empty:
            groups[column] = df.groupby(column, dropna=False, observed=False)[
                list(numeric.columns)
            ].mean().round(4).to_dict()
    return {
        "descriptive_statistics": stats,
        "correlations": correlations,
        "group_means": groups,
        "distributions": {
            column: {
                "count": int(df[column].count()),
                "mean": float(df[column].mean()),
                "median": float(df[column].median()),
                "std": float(df[column].std()) if df[column].count() > 1 else 0.0,
                "min": float(df[column].min()),
                "max": float(df[column].max()),
            }
            for column in numeric.columns
            if df[column].notna().any()
        },
    }
