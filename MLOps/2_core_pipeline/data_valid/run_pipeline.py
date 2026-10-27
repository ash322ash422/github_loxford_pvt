"""Read -> validate -> stop on failure, or prepare data for later ML training."""
from pathlib import Path
import argparse
import pandas as pd
from validate_data import ROOT, validate_data, result_table, save_report
from transform_data import transform_data


def run_pipeline(input_path):
    input_path = Path(input_path)
    data = pd.read_csv(input_path)
    result = validate_data(data)
    print(result_table(result).to_string(index=False))
    print("Report:", save_report(result, input_path.stem))
    if not result.success:
        print("STOP: validation failed. No feature engineering or new training file.")
        return False

    # The pipeline decides to stop. GX supplies the validation result.
    prepared = transform_data(data)
    output = ROOT / "output" / f"{input_path.stem}_features.csv"
    output.parent.mkdir(exist_ok=True)
    prepared.to_csv(output, index=False)
    print("PASS: prepared data for later model training:", output)
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=ROOT / "data/houses_clean.csv")
    args = parser.parse_args()
    raise SystemExit(0 if run_pipeline(args.input) else 1)
