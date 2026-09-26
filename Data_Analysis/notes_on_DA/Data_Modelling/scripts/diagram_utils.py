"""Shared helpers for building clean ER-style diagrams with matplotlib."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D

# Palette (brand-neutral, consistent across all diagrams)
FACT_HEADER = "#2F5D8A"     # deep blue for fact tables
DIM_HEADER  = "#3E8E7E"     # teal for dimension tables
SNOWFLAKE_HEADER = "#6C8EBF" # lighter blue for outrigger/snowflaked tables
HEADER_TEXT = "#FFFFFF"
BODY_BG = "#FFFFFF"
BODY_TEXT = "#1F2933"
BORDER = "#B0BEC5"
KEY_COLOR = "#C0392B"
LINE_COLOR = "#7F8C8D"
FIG_BG = "#FFFFFF"

def draw_table(ax, x, y, w, title, fields, header_color=DIM_HEADER, row_h=0.34, pk_fields=None, fk_fields=None):
    """
    Draw a table box with a colored header and rows of field names.
    (x, y) = top-left corner. Returns (bottom_y, height) and a dict of
    anchor points {field_name: (x_left, x_right, y_mid)} for connecting lines.
    """
    pk_fields = pk_fields or []
    fk_fields = fk_fields or []
    header_h = 0.42
    n = len(fields)
    total_h = header_h + n * row_h

    # Header
    ax.add_patch(FancyBboxPatch((x, y - header_h), w, header_h,
                                 boxstyle="round,pad=0,rounding_size=0.05",
                                 linewidth=0, facecolor=header_color, zorder=3))
    ax.text(x + w / 2, y - header_h / 2, title, ha="center", va="center",
            color=HEADER_TEXT, fontsize=11.5, fontweight="bold", zorder=4)

    # Body
    body_top = y - header_h
    ax.add_patch(Rectangle((x, body_top - n * row_h), w, n * row_h,
                            linewidth=1, edgecolor=BORDER, facecolor=BODY_BG, zorder=2))

    anchors = {}
    for i, field in enumerate(fields):
        row_y = body_top - i * row_h - row_h / 2
        is_pk = field in pk_fields
        is_fk = field in fk_fields
        label = field
        weight = "bold" if is_pk else "normal"
        color = KEY_COLOR if is_pk else (SNOWFLAKE_HEADER if is_fk else BODY_TEXT)
        prefix = "PK " if is_pk else ("FK " if is_fk else "")
        ax.text(x + 0.15, row_y, prefix + label, ha="left", va="center",
                fontsize=9.5, color=color, fontweight=weight, zorder=4)
        if i < n - 1:
            ax.plot([x, x + w], [body_top - (i + 1) * row_h, body_top - (i + 1) * row_h],
                    color=BORDER, linewidth=0.6, zorder=3)
        anchors[field] = (x, x + w, row_y)

    bottom_y = body_top - n * row_h
    return bottom_y, total_h, anchors


def connect(ax, p1, p2, style="-", color=LINE_COLOR, lw=1.4):
    ax.add_line(Line2D([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=lw,
                        solid_capstyle="round", zorder=1))


def new_fig(figsize=(11, 7)):
    fig, ax = plt.subplots(figsize=figsize, dpi=200)
    ax.set_facecolor(FIG_BG)
    fig.patch.set_facecolor(FIG_BG)
    ax.axis("off")
    return fig, ax


HILITE = "#FFE082"      # highlight for changed values
NEWROW = "#D6EAF8"       # highlight for a brand-new row
HEAD_BG = "#37474F"

def draw_data_table(ax, x, y, col_widths, headers, rows, title=None,
                     highlight_cells=None, highlight_rows=None, row_h=0.42, header_h=0.46,
                     fontsize=9.5, title_fontsize=11.5):
    """
    Draw a literal spreadsheet-style data table (for SCD / normalization examples).
    highlight_cells: set of (row_index, col_index) -> HILITE background (changed values)
    highlight_rows: dict {row_index: color} -> whole-row background tint
    """
    highlight_cells = highlight_cells or set()
    highlight_rows = highlight_rows or {}
    total_w = sum(col_widths)
    top = y
    if title:
        ax.text(x, top + 0.18, title, ha="left", va="bottom", fontsize=title_fontsize,
                fontweight="bold", color="#1F2933")

    # header row
    cx = x
    for j, h in enumerate(headers):
        ax.add_patch(Rectangle((cx, top - header_h), col_widths[j], header_h,
                                facecolor=HEAD_BG, edgecolor="white", linewidth=1, zorder=2))
        ax.text(cx + col_widths[j] / 2, top - header_h / 2, h, ha="center", va="center",
                color="white", fontsize=fontsize, fontweight="bold", zorder=3)
        cx += col_widths[j]

    # body rows
    for i, row in enumerate(rows):
        ry = top - header_h - i * row_h
        row_bg = highlight_rows.get(i, BODY_BG)
        cx = x
        for j, val in enumerate(row):
            cell_bg = HILITE if (i, j) in highlight_cells else row_bg
            ax.add_patch(Rectangle((cx, ry - row_h), col_widths[j], row_h,
                                    facecolor=cell_bg, edgecolor=BORDER, linewidth=0.8, zorder=2))
            ax.text(cx + col_widths[j] / 2, ry - row_h / 2, str(val), ha="center", va="center",
                    fontsize=fontsize, color=BODY_TEXT, zorder=3)
            cx += col_widths[j]

    bottom = top - header_h - len(rows) * row_h
    return bottom


def save(fig, path):
    fig.savefig(path, bbox_inches="tight", facecolor=FIG_BG)
    plt.close(fig)
    print("saved", path)
