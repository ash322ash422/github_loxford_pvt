"""
toolkits/viz_toolkit.py
Tools available to the Reporting Agent:
  • choose_chart_type  — LLM-friendly tool to declare which chart to render
  • generate_narrative — writes a full English report narrative
"""

from langchain_core.tools import tool


@tool
def choose_chart_type(chart_type: str, title: str) -> str:
    """
    Declare which chart type best suits the data.
    chart_type must be one of: bar, line, scatter, pie, histogram.
    title is a concise, descriptive chart title.
    Returns a JSON confirmation string.
    """
    valid = {"bar", "line", "scatter", "pie", "histogram"}
    ct = chart_type.lower().strip()
    if ct not in valid:
        ct = "bar"
    return f'{{"chart_type": "{ct}", "title": "{title}"}}'


@tool
def generate_narrative(narrative: str) -> str:
    """
    Provide a well-written, 3-5 paragraph narrative report for the query results.
    narrative should be a complete analysis including key findings, trends,
    and business recommendations.
    Returns the narrative as-is for inclusion in the PDF report.
    """
    return narrative
