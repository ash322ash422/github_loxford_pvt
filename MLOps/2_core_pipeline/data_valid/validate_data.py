"""Step 2: check a dataframe with Great Expectations and explain the results."""
from pathlib import Path
import argparse
import json
import pandas as pd
import great_expectations as gx
from expectations import make_suite

ROOT = Path(__file__).resolve().parent


def validate_data(data):
    # Ephemeral means in memory: no GX project folders or cloud account needed.
    context = gx.get_context(mode="ephemeral")
    context.enable_analytics(False)
    context.variables.progress_bars = {"globally": False}
    source = context.data_sources.add_pandas(name="housing_source")
    asset = source.add_dataframe_asset(name="housing_table")
    batch = asset.add_batch_definition_whole_dataframe(name="all_rows")
    suite = context.suites.add(make_suite())
    validation = context.validation_definitions.add(gx.ValidationDefinition(
        name="check_houses", data=batch, suite=suite,
    ))
    
    # Failed or uncomputable column rules are reported, rather than ignored.
    return validation.run(batch_parameters={"dataframe": data})


def result_table(result):
    """A compact teaching view; GX also provides a detailed JSON result."""
    rows = []
    for check in result.results:
        config = check.expectation_config
        raised = check.exception_info.get("raised_exception", False)
        rows.append({
            "rule": config.type,
            "column": config.kwargs.get("column", "(whole table)"),
            "passed": bool(check.success),
            "unexpected_count": check.result.get("unexpected_count"),
            "note": "Could not evaluate; inspect JSON details" if raised else "",
        })
        
    return pd.DataFrame(rows)


def save_report(result, name):
    folder = ROOT / "reports"
    folder.mkdir(exist_ok=True)
    path = folder / f"{name}.json"
    path.write_text(json.dumps(result.to_json_dict(), indent=2), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to a housing CSV")
    args = parser.parse_args()
    result = validate_data(pd.read_csv(args.input))
    print(result_table(result).to_string(index=False))
    print("Overall passed:", result.success)
    print("Report:", save_report(result, args.input.stem))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
