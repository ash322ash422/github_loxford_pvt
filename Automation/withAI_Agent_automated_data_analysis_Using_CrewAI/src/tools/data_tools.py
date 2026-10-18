from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load a CSV or Excel dataset and fail with an actionable error."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Dataset does not exist: {source}")
    if source.suffix.lower() == ".csv":
        return pd.read_csv(source)
    if source.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(source)
    raise ValueError("Unsupported dataset format. Use .csv, .xlsx, or .xls.")


def profile_dataset(df: pd.DataFrame) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    numeric = df.select_dtypes(include=np.number)
    missing = df.isna().sum()
    outliers: dict[str, int] = {}
    for column in numeric.columns:
        values = numeric[column].dropna()
        if values.empty:
            outliers[column] = 0
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        outliers[column] = (
            0
            if iqr == 0
            else int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
        )
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_types": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "numeric_columns": list(numeric.columns),
        "categorical_columns": list(df.select_dtypes(exclude=np.number).columns),
        "missing_values": {key: int(value) for key, value in missing.items() if value},
        "duplicate_rows": int(df.duplicated().sum()),
        "outliers_by_column": outliers,
    }


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    cleaned = df.copy()
    before_rows = len(cleaned)
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    numeric_columns = cleaned.select_dtypes(include=np.number).columns
    categorical_columns = cleaned.select_dtypes(exclude=np.number).columns
    for column in numeric_columns:
        if cleaned[column].isna().any():
            median = cleaned[column].median()
            cleaned[column] = cleaned[column].fillna(0 if pd.isna(median) else median)
    for column in categorical_columns:
        if cleaned[column].isna().any():
            cleaned[column] = cleaned[column].fillna("Unknown")
    missing_by_column = {
        column: int(count)
        for column, count in cleaned.isna().sum().items()
        if count
    }
    return cleaned, {
        "rows_before": before_rows,
        "rows_after": int(len(cleaned)),
        "duplicates_removed": int(before_rows - len(cleaned)),
        "missing_values_after": int(cleaned.isna().sum().sum()),
        "missing_values_after_by_column": missing_by_column,
        "numeric_imputation": "median",
        "categorical_imputation": "Unknown",
    }
