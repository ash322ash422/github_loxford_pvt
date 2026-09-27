"""
reports/pdf_report.py
Generates a styled PDF report from a query result.
Returns the PDF as bytes so Streamlit can offer a download button.
"""

import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


BRAND_BLUE  = colors.HexColor("#2980b9")
BRAND_DARK  = colors.HexColor("#2c3e50")
LIGHT_GREY  = colors.HexColor("#ecf0f1")
WHITE       = colors.white


def _df_to_table_data(df: pd.DataFrame, max_rows: int = 30):
    """Convert DataFrame to list-of-lists for ReportLab Table."""
    df_show = df.head(max_rows)
    header  = list(df_show.columns)
    rows    = [header] + df_show.astype(str).values.tolist()
    return rows


def _fig_to_image(fig: plt.Figure) -> Image | None:
    if fig is None:
        return None
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return Image(buf, width=16 * cm, height=8 * cm)


def generate_pdf(
    question: str,
    sql: str,
    df: pd.DataFrame,
    summary: str,
    fig: plt.Figure | None = None,
) -> bytes:
    """Build a PDF and return it as bytes."""

    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=WHITE,
        backColor=BRAND_DARK,
        spaceAfter=4,
        spaceBefore=4,
        alignment=TA_CENTER,
        borderPad=8,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=BRAND_BLUE,
        spaceBefore=14,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=BRAND_DARK,
    )
    code_style = ParagraphStyle(
        "Code",
        parent=styles["Code"],
        fontSize=8,
        backColor=LIGHT_GREY,
        borderPad=6,
        leading=12,
    )

    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    story.append(Paragraph("📊 NL-to-SQL Query Report", title_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
        ParagraphStyle("sub", parent=body_style, textColor=colors.grey, alignment=TA_CENTER)
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceAfter=10))

    # ── Question ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Question", section_style))
    story.append(Paragraph(question, body_style))
    story.append(Spacer(1, 0.3 * cm))

    # ── SQL ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Generated SQL", section_style))
    safe_sql = sql.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    story.append(Paragraph(safe_sql, code_style))
    story.append(Spacer(1, 0.3 * cm))

    # ── Summary ───────────────────────────────────────────────────────────────
    story.append(Paragraph("AI Summary", section_style))
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 0.3 * cm))

    # ── Chart ─────────────────────────────────────────────────────────────────
    if fig is not None:
        story.append(Paragraph("Visualisation", section_style))
        img = _fig_to_image(fig)
        if img:
            story.append(img)
        story.append(Spacer(1, 0.3 * cm))

    # ── Data Table ────────────────────────────────────────────────────────────
    story.append(Paragraph(f"Query Results  (showing up to 30 of {len(df)} rows)", section_style))
    story.append(Spacer(1, 0.2 * cm))

    table_data = _df_to_table_data(df)
    n_cols     = len(table_data[0])
    col_width  = (17 * cm) / n_cols

    tbl = Table(table_data, colWidths=[col_width] * n_cols, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",  (0, 0), (-1, 0),  BRAND_DARK),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        ("BOTTOMPADDING",(0,0), (-1, 0),  6),
        # Data rows
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#bdc3c7")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING",(0,1), (-1, -1), 4),
    ]))
    story.append(tbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "Confidential — Auto-generated by NL-to-SQL Report Engine",
        ParagraphStyle("footer", parent=body_style, fontSize=8,
                       textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()
