from __future__ import annotations

import argparse
import json
from pathlib import Path
from src.crew import run_pipeline

def main() -> None:
    
    parser = argparse.ArgumentParser(description="Run the automated data analysis crew.")
    parser.add_argument("dataset", type=Path, help="Path to a CSV or Excel dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Directory for cleaned data, charts, and the report.",
    )
    args = parser.parse_args()
    result = run_pipeline(args.dataset, args.output)
    print(json.dumps({
        "cleaned_dataset": result["cleaned_dataset"],
        "visualizations": result["visualizations"],
        "report": str(args.output / "analysis_report.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
