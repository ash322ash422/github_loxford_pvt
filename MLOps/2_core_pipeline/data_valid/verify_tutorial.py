"""Optional instructor checks for the examples and the pipeline's stop condition."""
from unittest.mock import patch
import pandas as pd
from get_data import get_data
from validate_data import ROOT, validate_data, result_table
from run_pipeline import run_pipeline


def verify():
    get_data()
    clean = pd.read_csv(ROOT / "data/houses_clean.csv")
    assert validate_data(clean).success
    for example in ["dirty", "bad_schema", "bad_type"]:
        path = ROOT / f"data/houses_{example}.csv"
        result = validate_data(pd.read_csv(path))
        assert not result.success, f"{example} should fail"
        failed = result_table(result).query("passed == False")
        print(f"{example}: rejected ({len(failed)} failing rules)")
        # A failed validation must prevent the next pipeline function from running.
        with patch("run_pipeline.transform_data") as transform:
            assert not run_pipeline(path)
            transform.assert_not_called()
    assert not validate_data(clean.iloc[:0]).success, "An empty table must fail"
    assert run_pipeline(ROOT / "data/houses_clean.csv")
    output = pd.read_csv(ROOT / "output/houses_clean_features.csv")
    assert len(output) == len(clean)
    assert "area_per_bedroom" in output
    pd.testing.assert_series_equal(
        output.area_per_bedroom, clean.area_sqft / clean.bedrooms,
        check_names=False,
    )
    print("PASS: clean input accepted; bad input rejected; feature preparation is gated.")


if __name__ == "__main__":
    verify()
