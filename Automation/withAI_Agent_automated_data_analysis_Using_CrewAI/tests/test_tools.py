from pathlib import Path

import pandas as pd

from src.crew import run_pipeline
from src.tools.data_tools import clean_dataset, profile_dataset


def test_profile_and_clean_handle_duplicates_and_missing_values() -> None:
    frame = pd.DataFrame(
        {"group": ["A", "A", "B"], "score": [80.0, 80.0, None]}
    )

    profile = profile_dataset(frame)
    cleaned, summary = clean_dataset(frame)

    assert profile["duplicate_rows"] == 1
    assert profile["missing_values"] == {"score": 1}
    assert summary["duplicates_removed"] == 1
    assert summary["missing_values_after"] == 0
    assert cleaned["score"].tolist() == [80.0, 80.0]


def test_pipeline_writes_outputs_for_non_numeric_data(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "categorical.csv"
    pd.DataFrame({"name": ["A", "B"], "group": ["x", "y"]}).to_csv(
        source, index=False
    )

    monkeypatch.setattr(
        "src.ai_crew.run_agent_crew",
        lambda dataset_path, output_dir: (
            Path(output_dir).mkdir(parents=True, exist_ok=True),
            Path(output_dir, "analysis_report.md").write_text(
                "# AI report\n", encoding="utf-8"
            ),
            {"task_outputs": ["AI crew completed"]},
        )[-1],
    )
    result = run_pipeline(source, tmp_path / "output")

    assert result["analysis"]["descriptive_statistics"] == {}
    assert result["visualizations"] == []
    assert result["quality_review"]["approved"] is True
    assert (tmp_path / "output" / "analysis_report.md").exists()


def test_pipeline_handles_an_all_missing_numeric_column(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "missing.csv"
    pd.DataFrame({"score": [None, None]}).to_csv(source, index=False)

    monkeypatch.setattr(
        "src.ai_crew.run_agent_crew",
        lambda dataset_path, output_dir: (
            Path(output_dir).mkdir(parents=True, exist_ok=True),
            Path(output_dir, "analysis_report.md").write_text(
                "# AI report\n", encoding="utf-8"
            ),
            {"task_outputs": ["AI crew completed"]},
        )[-1],
    )
    result = run_pipeline(source, tmp_path / "output")

    assert result["cleaning"]["missing_values_after"] == 0
    assert result["analysis"]["distributions"]["score"]["mean"] == 0.0
