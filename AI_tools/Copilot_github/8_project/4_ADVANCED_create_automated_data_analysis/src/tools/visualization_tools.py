from __future__ import annotations

from pathlib import Path
import re

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


def create_visualizations(df: pd.DataFrame, output_dir: str | Path) -> list[str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return files
    for column in numeric.columns:
        safe_column = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(column)).strip("._") or "column"
        path = destination / f"{safe_column}_distribution.png"
        plt.figure(figsize=(8, 5))
        sns.histplot(data=df, x=column, kde=df[column].nunique(dropna=True) > 1)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        files.append(str(path))
    if len(numeric.columns) > 1:
        path = destination / "correlation_heatmap.png"
        plt.figure(figsize=(8, 6))
        sns.heatmap(numeric.corr(), annot=True, cmap="vlag", center=0)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        files.append(str(path))
    return files
