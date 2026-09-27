"""
graphs/charts.py
Visualization Toolkit — renders charts from a DataFrame.
Supports: bar, line, scatter, pie, histogram.
All charts use a dark theme consistent with Streamlit's dark mode.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Theme ──────────────────────────────────────────────────────────────────────
BG       = "#0e1117"
CARD     = "#1a1f2e"
ACCENT   = "#4f8ef7"
PALETTE  = ["#4f8ef7","#e05c5c","#2ecc71","#f39c12","#9b59b6",
            "#1abc9c","#e67e22","#e91e8c","#00bcd4","#ff7043"]
TEXT     = "#e0e0e0"
GRID     = "#2a2f3e"


def _base_fig(w=10, h=5):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.grid(axis="y", color=GRID, linestyle="--", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def _bar(df, title):
    text_cols = df.select_dtypes("object").columns.tolist()
    num_cols  = df.select_dtypes("number").columns.tolist()
    if not text_cols or not num_cols:
        return None

    x_col = text_cols[0]; y_col = num_cols[0]
    tmp   = df[[x_col, y_col]].dropna().head(20).sort_values(y_col, ascending=False)

    fig, ax = _base_fig(11, 5)
    colors  = [PALETTE[i % len(PALETTE)] for i in range(len(tmp))]
    bars    = ax.bar(range(len(tmp)), tmp[y_col], color=colors,
                     edgecolor=BG, linewidth=0.5, width=0.65)

    ax.set_xticks(range(len(tmp)))
    ax.set_xticklabels(tmp[x_col].astype(str), rotation=35,
                       ha="right", fontsize=8, color=TEXT)
    ax.set_ylabel(y_col, color=TEXT, fontsize=10)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)

    for bar, val in zip(bars, tmp[y_col]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.01,
                f"{val:,.0f}", ha="center", va="bottom", fontsize=7.5, color=TEXT)

    fig.tight_layout()
    return fig


def _line(df, title):
    date_cols = [c for c in df.columns if "date" in c.lower() or "month" in c.lower() or "year" in c.lower()]
    num_cols  = df.select_dtypes("number").columns.tolist()
    if not num_cols:
        return None

    x_col = date_cols[0] if date_cols else df.columns[0]
    fig, ax = _base_fig(11, 5)

    for i, y_col in enumerate(num_cols[:4]):
        tmp = df[[x_col, y_col]].dropna()
        if date_cols:
            tmp[x_col] = pd.to_datetime(tmp[x_col], errors="coerce")
            tmp = tmp.dropna().sort_values(x_col)
        ax.plot(tmp[x_col], tmp[y_col], color=PALETTE[i], lw=2.2,
                marker="o", markersize=4, label=y_col)
        ax.fill_between(tmp[x_col], tmp[y_col], alpha=0.07, color=PALETTE[i])

    ax.set_xlabel(x_col, color=TEXT, fontsize=10)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)
    if len(num_cols) > 1:
        ax.legend(facecolor=CARD, edgecolor=GRID, labelcolor=TEXT, fontsize=8)
    if date_cols:
        fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def _scatter(df, title):
    num_cols = df.select_dtypes("number").columns.tolist()
    if len(num_cols) < 2:
        return None
    x_col, y_col = num_cols[0], num_cols[1]
    fig, ax = _base_fig(9, 5)
    ax.scatter(df[x_col], df[y_col], color=ACCENT, alpha=0.55,
               edgecolors="none", s=35)
    # Trend line
    mask = df[[x_col,y_col]].dropna()
    if len(mask) > 2:
        z = np.polyfit(mask[x_col], mask[y_col], 1)
        p = np.poly1d(z)
        xs = np.linspace(mask[x_col].min(), mask[x_col].max(), 200)
        ax.plot(xs, p(xs), color="#e05c5c", lw=1.5, linestyle="--", label="Trend")
        ax.legend(facecolor=CARD, edgecolor=GRID, labelcolor=TEXT, fontsize=8)
    ax.set_xlabel(x_col, color=TEXT, fontsize=10)
    ax.set_ylabel(y_col, color=TEXT, fontsize=10)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return fig


def _pie(df, title):
    text_cols = df.select_dtypes("object").columns.tolist()
    num_cols  = df.select_dtypes("number").columns.tolist()
    if not text_cols or not num_cols:
        return None
    label_col = text_cols[0]; val_col = num_cols[0]
    tmp = df[[label_col, val_col]].dropna().head(8)

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

    wedges, texts, autotexts = ax.pie(
        tmp[val_col],
        labels      = tmp[label_col].astype(str),
        colors      = PALETTE[:len(tmp)],
        autopct     = "%1.1f%%",
        startangle  = 140,
        pctdistance = 0.82,
        wedgeprops  = dict(edgecolor=BG, linewidth=1.5),
    )
    for t in texts:    t.set_color(TEXT); t.set_fontsize(9)
    for t in autotexts: t.set_color(BG); t.set_fontsize(8); t.set_fontweight("bold")

    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return fig


def _histogram(df, title):
    num_cols = df.select_dtypes("number").columns.tolist()
    if not num_cols:
        return None
    col = num_cols[0]
    fig, ax = _base_fig(9, 5)
    n, bins, patches = ax.hist(df[col].dropna(), bins=25,
                                color=ACCENT, edgecolor=BG, linewidth=0.5)
    # Colour gradient
    for i, patch in enumerate(patches):
        patch.set_facecolor(PALETTE[i % len(PALETTE)])
    ax.set_xlabel(col, color=TEXT, fontsize=10)
    ax.set_ylabel("Count", color=TEXT, fontsize=10)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return fig


# ── Public entry point ─────────────────────────────────────────────────────────
def build_chart(df: pd.DataFrame, chart_type: str, title: str):
    """Build and return a matplotlib Figure for the given chart_type."""
    dispatch = {
        "bar":       _bar,
        "line":      _line,
        "scatter":   _scatter,
        "pie":       _pie,
        "histogram": _histogram,
    }
    fn = dispatch.get(chart_type, _bar)
    return fn(df, title)
