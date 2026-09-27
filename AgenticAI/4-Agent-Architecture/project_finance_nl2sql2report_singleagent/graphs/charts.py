"""
graphs/charts.py
Auto-generates a Matplotlib figure from a DataFrame.
Returns a plt.Figure so Streamlit can render it with st.pyplot().
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


# Colour palette
PALETTE = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
           "#1abc9c", "#e67e22", "#34495e"]


def _format_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")


def auto_chart(df: pd.DataFrame, question: str = "") -> plt.Figure | None:
    """
    Heuristic chart selection:
    - 1 numeric col              → histogram
    - 1 text + 1 numeric         → bar chart
    - 2 numeric cols             → scatter / line
    - date col + numeric         → line chart
    - else                       → bar of first text + numeric
    """
    if df is None or df.empty or len(df.columns) < 1:
        return None

    num_cols  = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()
    date_cols = [c for c in df.columns if "date" in c.lower()]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    ax.tick_params(colors="white")
    ax.yaxis.label.set_color("white")
    ax.xaxis.label.set_color("white")
    ax.title.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")
    ax.grid(axis="y", alpha=0.2, linestyle="--", color="#555")

    # ── Line chart for time series ────────────────────────────────────────────
    if date_cols and num_cols:
        dc = date_cols[0]
        nc = num_cols[0]
        tmp = df[[dc, nc]].dropna()
        tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
        tmp = tmp.dropna().sort_values(dc)
        ax.plot(tmp[dc], tmp[nc], color=PALETTE[0], lw=2, marker="o", markersize=4)
        ax.set_xlabel(dc, color="white")
        ax.set_ylabel(nc, color="white")
        ax.set_title(f"{nc} over time", color="white", fontweight="bold")
        fig.autofmt_xdate()
        return fig

    # ── Bar chart for category + numeric ─────────────────────────────────────
    if text_cols and num_cols:
        tc = text_cols[0]
        nc = num_cols[0]
        tmp = df[[tc, nc]].dropna().head(20)
        colors = [PALETTE[i % len(PALETTE)] for i in range(len(tmp))]
        bars = ax.bar(tmp[tc].astype(str), tmp[nc], color=colors)
        ax.set_xlabel(tc, color="white")
        ax.set_ylabel(nc, color="white")
        ax.set_title(f"{nc} by {tc}", color="white", fontweight="bold")
        plt.xticks(rotation=35, ha="right", color="white")
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01,
                    f"{h:,.0f}", ha="center", va="bottom", fontsize=8, color="white")
        return fig

    # ── Histogram for a single numeric ───────────────────────────────────────
    if len(num_cols) == 1:
        nc = num_cols[0]
        ax.hist(df[nc].dropna(), bins=20, color=PALETTE[0], edgecolor="#0e1117")
        ax.set_xlabel(nc, color="white")
        ax.set_ylabel("Count", color="white")
        ax.set_title(f"Distribution of {nc}", color="white", fontweight="bold")
        return fig

    # ── Scatter for two numeric cols ──────────────────────────────────────────
    if len(num_cols) >= 2:
        x, y = num_cols[0], num_cols[1]
        ax.scatter(df[x], df[y], color=PALETTE[0], alpha=0.6, edgecolors="none", s=30)
        ax.set_xlabel(x, color="white")
        ax.set_ylabel(y, color="white")
        ax.set_title(f"{y} vs {x}", color="white", fontweight="bold")
        return fig

    return None
