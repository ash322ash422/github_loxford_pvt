from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .ai_crew import run_agent_crew
from .tools.analysis_tools import analyze_dataset
from .tools.data_tools import clean_dataset, load_dataset, profile_dataset
from .tools.visualization_tools import create_visualizations


def generate_insights(analysis: dict[str, Any]) -> list[str]:
    insights: list[str] = []
    for column, values in analysis["distributions"].items():
        if values["mean"] == values["median"]:
            direction = "equal to"
        else:
            direction = "above" if values["mean"] > values["median"] else "below"
        insights.append(
            f"{column}: mean ({values['mean']:.2f}) is {direction} the median "
            f"({values['median']:.2f})."
        )
    for left, related in analysis["correlations"].items():
        for right, value in related.items():
            if left < right and value is not None and abs(value) >= 0.7:
                strength = "positive" if value > 0 else "negative"
                insights.append(
                    f"{left} and {right} have a strong {strength} correlation "
                    f"({value:.2f}); this is an association, not proof of causation."
                )
    return insights or ["No numeric columns were available for automated insights."]


def quality_review(package: dict[str, Any]) -> dict[str, Any]:
    """Validate the tool outputs before publishing the report."""
    checks = {
        "cleaned_data_has_no_missing_values": package["cleaning"]["missing_values_after"] == 0,
        "cleaned_rows_match_summary": package["cleaning"]["rows_after"]
        == package["analysis"]["row_count"],
        "visualizations_exist": all(Path(path).exists() for path in package["visualizations"]),
        "insights_present": bool(package["insights"]),
    }
    return {"approved": all(checks.values()), "checks": checks}


def render_report(package: dict[str, Any], report_path: Path) -> None:
    profile = package["profile"]
    cleaning = package["cleaning"]
    lines = [
        "# Automated Data Analysis Report",
        "",
        "## Executive summary",
        f"The dataset contains {profile['rows']} rows and {profile['columns']} columns.",
        f"Cleaning removed {cleaning['duplicates_removed']} duplicate rows and left "
        f"{cleaning['missing_values_after']} missing values.",
        "",
        "## Dataset profile",
        f"- Numeric columns: {', '.join(profile['numeric_columns']) or 'None'}",
        f"- Categorical columns: {', '.join(profile['categorical_columns']) or 'None'}",
        f"- Duplicate rows: {profile['duplicate_rows']}",
        f"- Missing values: {profile['missing_values'] or 'None'}",
        f"- Outliers by column: {profile['outliers_by_column'] or 'None'}",
        "",
        "## Cleaning summary",
        f"- Rows before cleaning: {cleaning['rows_before']}",
        f"- Rows after cleaning: {cleaning['rows_after']}",
        f"- Numeric missing values were replaced with the column median "
        f"(or 0 when a column was entirely missing).",
        f"- Categorical missing values were replaced with `Unknown`.",
        "",
        "## Analysis",
        f"- Rows analyzed: {package['analysis']['row_count']}",
        f"- Descriptive statistics: `{package['analysis']['descriptive_statistics']}`",
        f"- Group means: `{package['analysis']['group_means'] or 'None'}`",
        f"- Correlations: `{package['analysis']['correlations'] or 'None'}`",
        "",
        "## Insights",
    ]
    lines.extend(f"- {insight}" for insight in package["insights"])
    lines.extend(["", "## Visualizations"])
    lines.extend(f"- [{Path(path).name}]({Path(path).as_posix()})" for path in package["visualizations"])
    lines.extend(
        [
            "",
            "## Quality review",
            f"- Status: {'APPROVED' if package['quality_review']['approved'] else 'REVISE'}",
        ]
    )
    lines.extend(
        f"- {check}: {'PASS' if passed else 'FAIL'}"
        for check, passed in package["quality_review"]["checks"].items()
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(dataset_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    ai_result = run_agent_crew(dataset_path, output_dir)
    raw = load_dataset(dataset_path)
    profile = profile_dataset(raw)
    cleaned, cleaning = clean_dataset(raw)
    cleaned_path = destination / "cleaned_data.csv"
    cleaned.to_csv(cleaned_path, index=False)
    analysis = analyze_dataset(cleaned)
    analysis["row_count"] = int(len(cleaned))
    visualizations = create_visualizations(cleaned, destination / "visualizations")
    package = {
        "profile": profile,
        "cleaning": cleaning,
        "analysis": analysis,
        "visualizations": visualizations,
        "insights": generate_insights(analysis),
        "cleaned_dataset": str(cleaned_path),
    }
    package["ai_task_outputs"] = ai_result["task_outputs"]
    package["quality_review"] = quality_review(package)
    if not package["quality_review"]["approved"]:
        failed = [
            check for check, passed in package["quality_review"]["checks"].items() if not passed
        ]
        raise RuntimeError(f"Quality review failed: {', '.join(failed)}")
    if not (destination / "analysis_report.md").exists():
        raise RuntimeError("The AI Report Writer did not produce analysis_report.md.")
    return package
