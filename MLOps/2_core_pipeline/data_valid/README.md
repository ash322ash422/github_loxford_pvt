# Data validation with Great Expectations

**Can we trust this data before we use it?** This beginner lesson uses a small
synthetic house-price dataset to answer that question.

Great Expectations (also called GX) is a Python library for checking data against
rules you define. A rule is an **Expectation**. For example, every house should
have an area, and a sale price should be positive. A collection of rules is an
**Expectation Suite**. Running those rules produces a **Validation Result**.

## Why do we need it?

A CSV can load successfully even when it contains missing areas, negative
prices, duplicate house IDs, or the wrong columns. A model may fail later or
learn from incorrect data. Instead of repeatedly inspecting each incoming file
by hand, we define reusable checks and run them on every delivery.

| Problem | What we check |
| --- | --- |
| A required column disappeared | Schema: expected column names |
| Price contains text such as `unknown` | Schema: expected data types |
| Some houses have no area | Missing values |
| A house has zero bedrooms or a negative price | Allowed ranges |
| Two rows use the same house ID | Uniqueness |

Passing these checks means the data meets **our chosen rules**. It does not
prove every value is factually correct or guarantee a good model. GX reports
problems; it does not automatically repair them.

## Run with the existing `.venv`

From `C:\Users\Ash\Desktop\educational\play_ML` in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r data_valid/requirements.txt
.\.venv\Scripts\python.exe data_valid/get_data.py
.\.venv\Scripts\python.exe data_valid/run_pipeline.py
```

The default pipeline validates the clean file, prints a table of checks, saves
a JSON report, and creates `data_valid/output/houses_clean_features.csv`.
No external dataset or GX Cloud account is required. Tested with Python 3.11
and Great Expectations 1.24.1. The requirements use the modern GX 1.x API;
older tutorials using `gx.from_pandas()` do not match this example.

## Open the teaching notebook

Open **`teaching_data_validation.ipynb`** in VS Code or Jupyter and select the
existing `.venv` Python kernel. Start with the project root or `data_valid` as
the working directory, then run cells from top to bottom.

The notebook includes explanations, helpful code comments, and short tables.
It follows this sequence:

1. Inspect a five-column housing dataset.
2. Understand schema checks versus missing-value checks.
3. Write one Great Expectations rule and see a pass and a failure.
4. Reuse a suite of rules on clean and dirty data.
5. Detect a missing column and an incorrect data type.
6. Add validation as a gate before feature engineering.
7. Try a small exercise by changing the data or a rule.

## The synthetic dataset

`get_data.py` creates 100 houses with a fixed random seed. Each row represents
one house, so IDs must be unique in this lesson.

| Column | Expected data |
| --- | --- |
| `house_id` | Integer, present, unique |
| `area_sqft` | Decimal number, present, between 300 and 10,000 |
| `bedrooms` | Integer, present, between 1 and 10 |
| `year_built` | Integer, present, between 1900 and 2026 |
| `sale_price` | Decimal number, present, between 10,000 and 5,000,000 |

Ranges are inclusive. These are classroom assumptions, not universal rules
for every housing market. The schema expects exactly these five columns, but
their order may vary. The table must have at least one row.

The generator saves four example deliveries:

- `houses_clean.csv`: meets every rule.
- `houses_dirty.csv`: two missing areas, a negative price, zero bedrooms, and
  a duplicated house ID.
- `houses_bad_schema.csv`: the `bedrooms` column is missing.
- `houses_bad_type.csv`: one price is the text `unknown`.

Missing checks are separate from numeric range checks: a range check can ignore
null values. Likewise, a numeric value may still be outside an acceptable range.
This is why we need more than a check that the file opens.

## How the Great Expectations code works

`expectations.py` holds the rules in one reusable function, `make_suite()`.
For example:

```python
gx.expectations.ExpectColumnValuesToNotBeNull(column="area_sqft")
gx.expectations.ExpectColumnValuesToBeBetween(
    column="bedrooms", min_value=1, max_value=10,
)
```

`validate_data.py` runs the rules against a pandas dataframe. GX uses a few
objects to connect the rules to the data:

| GX term | Simple meaning here |
| --- | --- |
| Data Context | The workspace managing our GX objects |
| Data Source / Data Asset | The connection to our pandas table |
| Batch | The rows we are checking; here, the whole dataframe |
| Expectation Suite | The reusable list of rules |
| Validation Definition | Connects the batch definition to the suite |
| Validation Result | Overall pass/fail and details for each rule |

Our Context stays in memory (`ephemeral`), so we do not need to create a GX
project or learn configuration files. The same Python rules are reused by the
notebook and the pipeline. We explicitly save reports to `reports/`.

`result_table(result)` makes a short pandas summary. A false `passed` value
means a rule failed. `unexpected_count` is the number of offending rows when
GX supplies that metric; a blank/NaN means it is not available for that rule,
not that the check passed. The JSON report contains the detailed result.
Duplicate checks flag all occurrences of a repeated value, not just later rows.

If a column is absent or values cannot be compared, some column rules cannot
be evaluated. We catch these rule-evaluation errors and retain them as failures
in the report. They do not count as a pass. Read the schema/type failures first.

## Use validation in a pipeline

```text
Raw CSV -> Great Expectations validation -> PASS -> feature engineering -> output CSV
                                        -> FAIL -> report and stop
```

`run_pipeline.py` contains the important decision:

```python
result = validate_data(data)
if not result.success:
    return False
prepared = transform_data(data)
```

GX provides the result; **our pipeline chooses to stop**. We require every rule
to pass. `transform_data.py` then calculates `area_per_bedroom = area_sqft /
bedrooms`. Validation first avoids calculating this feature from missing areas
or zero bedrooms. The output could be used for later model training; training
is deliberately left out so the lesson focuses on data quality.

Try the dirty input:

```powershell
.\.venv\Scripts\python.exe data_valid/run_pipeline.py data_valid/data/houses_dirty.csv
```

Expect a STOP message and exit code **1**. That is the intended demonstration,
not a broken program. It writes a report but does not run feature engineering
or create a new output file. Previous successful outputs, if any, remain on disk.
Clean input exits with code **0**. Input paths supplied on the command line are
relative to your current working directory.

To validate without running any feature engineering:

```powershell
.\.venv\Scripts\python.exe data_valid/validate_data.py data_valid/data/houses_bad_schema.csv
.\.venv\Scripts\python.exe data_valid/validate_data.py data_valid/data/houses_bad_type.csv
```

## Files

| File | Purpose |
| --- | --- |
| `get_data.py` | Generate synthetic clean and deliberately bad raw data |
| `expectations.py` | Define reusable validation rules |
| `validate_data.py` | Run GX, summarize results, save JSON reports |
| `transform_data.py` | Simple feature engineering after validation |
| `run_pipeline.py` | Read, validate, stop or transform and save |
| `teaching_data_validation.ipynb` | Guided classroom lesson |
| `verify_tutorial.py` | Optional instructor checks |
| `requirements.txt` | Dependencies for the existing environment |

Optional instructor verification:

```powershell
.\.venv\Scripts\python.exe data_valid/verify_tutorial.py
```

This checks clean and bad data, an empty table, and that transformation never
runs on invalid input. JSON reports may include sample failed values; use
synthetic data when sharing the lesson. Reports overwrite the same named report
on a repeat run. Numeric dtype rules reflect pandas inference for these CSVs;
other ingestion formats may need different type expectations.

Official reading: [Try GX Core](https://docs.greatexpectations.io/docs/core/introduction/try_gx/),
[Expectations](https://docs.greatexpectations.io/docs/core/define_expectations/), and
[Data Contexts](https://docs.greatexpectations.io/docs/core/set_up_a_gx_environment/create_a_data_context/).
