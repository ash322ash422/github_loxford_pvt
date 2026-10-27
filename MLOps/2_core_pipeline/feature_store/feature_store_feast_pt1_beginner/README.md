# A gentle introduction to Feast

**Prepare features once. Reuse them in different models and in an application.**

Imagine two people building house-price models. Both need house size, bedrooms,
and house age. If each person writes their own preparation code, their inputs
can differ. A feature store gives them a shared place to retrieve ready-to-use
features.

In this lesson, we use **one prepared Feast data source, one entity, one feature view,
and four features**. Each model selects the features it needs from this shared view. Everything runs locally
in your existing Python `.venv`.

## 1. Run the example

From `C:\Users\Ash\Desktop\educational\play_ML` in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r feature_store_feast/requirements.txt
.\.venv\Scripts\python.exe feature_store_feast/run_demo.py
```

This generates raw data, prepares features, registers Feast definitions, trains two models,
and prints predictions. No dataset download or cloud account is needed.

For a guided lesson, open **`teaching_demo.ipynb`**, select the existing `.venv`
Python kernel, and run the cells in order. Start the notebook from this folder
or the project root.

## 2. Follow the data preparation pipeline

```text
get_data.py                transform_features.py             Feast
raw_housing.parquet  -->  housing.parquet               -->  two models
(raw observations)        (four prepared features)           and prediction
```

**Step 1: get the raw data.** `get_data.py` generates `data/raw_housing.parquet`
with house IDs, timestamps, area, bedrooms, year built, and synthetic prices.
It does not create `area_per_bedroom` or `house_age_years`.

**Step 2: engineer the features.** `transform_features.py` reads the raw file,
calls `transform_features(raw_data)`, and saves `data/housing.parquet`.
The function returns a prepared copy and leaves the raw dataframe unchanged.

**Step 3: give Feast the prepared data.** Feast reads only `housing.parquet`.
The raw file is an upstream pipeline input, not a second Feast source.
Parquet is a table file format, similar in purpose to CSV.

You can show these stages separately in Python:

```python
from get_data import get_data
from transform_features import transform_features

raw_data = get_data()
prepared_data = transform_features(raw_data)
```

The notebook displays both tables. To also save the prepared file for Feast,
run `prepare_features()` from `transform_features.py` or use the script commands
at the end of this README.

There are 100 houses, each observed monthly for 24 months: 2,400 rows total.
The dates end in the current month. Re-running uses the same random seed.
These are synthetic observations of possible prices, not actual repeated sales.

| Column | Meaning |
| --- | --- |
| `house_id` | Identifies a house; this is a lookup key, not a model input |
| `event_timestamp` | Date this snapshot describes |
| `year_built` | Used when preparing house age; not a model input |
| `area_sqft` | Feature 1: size of the house |
| `bedrooms` | Feature 2: number of bedrooms |
| `area_per_bedroom` | Feature 3: size divided by bedrooms |
| `house_age_years` | Feature 4: snapshot year minus year built |
| `sale_price` | The target the models learn to predict; not a feature |

The two engineered features are deliberately simple:

```python
data["area_per_bedroom"] = data["area_sqft"] / data["bedrooms"]
data["house_age_years"] = data["event_timestamp"].dt.year - data["year_built"]
```

These calculations live only in `transform_features.py`, before Feast reads
the prepared file. Neither model nor the prediction application repeats these calculations.
Feast only exposes the four columns named in its feature view; it does not
expose `sale_price` as an input.

## 3. Learn the basic Feast concepts

| Concept | Meaning in this example |
| --- | --- |
| **Entity** | The thing we describe: a house, identified by `house_id` |
| **Data source** | Where prepared data lives: `housing.parquet` |
| **Feature view** | A named group of the four house features: `house_features` |
| **Feature store** | The library we call to retrieve these shared features |

These definitions live in `feature_repo/definitions.py`.

`feast apply` registers them so Feast knows which features are available and
where to find them. It does **not** create the engineered values; our Python
code already did that.

Two storage terms become useful when we train and predict:

- **Offline store:** the history in our one Parquet file, used for training.
- **Online store:** a small SQLite database containing the latest feature values
  for each house, used for prediction.

The registry database records definitions. These Feast-managed databases are
not extra input datasets. Feast has **one file data source**, `housing.parquet`;
the raw file belongs to the earlier preparation step.
`feature_store.yaml` configures these local storage locations.

## 4. Why timestamps matter

Suppose house 1 was built in 2000:

| Snapshot | House age |
| --- | --- |
| January 2025 | 25 |
| January 2026 | 26 |

When training on a 2025 example, we want age **25**. When predicting using the
2026 snapshot, we want age **26**.

`get_historical_features()` retrieves the most recent feature snapshot at or
before each requested date. This is called a **point-in-time lookup**. It avoids
using future feature values for an old training example. The notebook shows the
same house at two dates so students can see its age change.

The feature view also sets a 40-day **TTL**: a historical lookup may use a
snapshot up to 40 days old. This accommodates our monthly snapshots. TTL does
not refresh data automatically. All training rows here have matching snapshots.

## 5. Train different models with different feature subsets

A model does not have to use every feature in the store. In `common.py`, we choose:

| Model | Features requested from Feast |
| --- | --- |
| Linear Regression | `area_sqft`, `bedrooms` (two features) |
| Random Forest | `area_sqft`, `bedrooms`, `area_per_bedroom`, `house_age_years` (four features) |

`train_models.py` loops over the models. For each one, it requests only that
model's selected columns from the same feature view:

```python
columns = MODEL_FEATURES[name]
feature_refs = [f"house_features:{column}" for column in columns]
training_data = fs.get_historical_features(
    entity_df=labels,
    features=feature_refs,
).to_df()
```

`labels` contains only house IDs, dates, and target prices. Feast adds the
requested input columns. Each model then trains on its own subset:

```python
X_train = training_data.loc[is_train, columns]
model.fit(X_train, y_train)
```

The terminal prints each model's feature names and test MAE. This demonstrates
that the feature store is a reusable library: models can select different inputs
without another feature engineering pipeline. Shared features still have the
same values for the same house and timestamp.

To experiment, edit `MODEL_FEATURES` in `common.py` and rerun `train_models.py`.
Always retrain after changing a model's feature list. Prediction uses that same
list, in the same column order.

The first 20 months train the models; the final four months test them. We print
**MAE**, the average absolute prediction error in synthetic dollars. Lower is
better. The same houses occur over time; this is a lesson in reuse, not a real
housing-price benchmark. Saved models and scores go into `artifacts/`.

## 6. Retrieve ready-to-use features for prediction

`materialize.py` copies the latest feature values into SQLite. Feast calls this
**materialization**.

`predict.py` asks for the latest features using only a house ID:

```python
features = store().get_online_features(
    features=FEATURE_REFS,
    entity_rows=[{"house_id": 1}],
).to_df()
```

It retrieves two features for Linear Regression and four for Random Forest,
then passes each subset to the matching saved model and prints its prediction. No size-per-bedroom or age calculation is repeated here.

The difference to remember:

- `get_historical_features()`: features for specific dates, for training.
- `get_online_features()`: latest materialized features, for prediction.

The notebook and application use the same feature names from `common.py`.
Feast makes the prepared features reusable; scikit-learn trains the models.

## 7. Optional: move from the notebook to FastAPI

After completing the main example, activate the existing environment and start
the small application:

```powershell
.\.venv\Scripts\Activate.ps1
cd feature_store_feast
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open [the prediction endpoint](http://127.0.0.1:8000/predict/1) or
[the API documentation](http://127.0.0.1:8000/docs).

The endpoint returns predictions from both models. `app.py` calls the exact same
`predict()` function used in the lesson. It needs a house ID, not another copy
of feature engineering code.

That is the notebook-to-application connection. Docker or AWS could run the
application later; they are outside this introductory lesson. A real deployment
also needs scheduled feature updates and shared storage. Online lookup returns
stored values; it does not recalculate today's house age. Rerun the demo to
refresh this classroom dataset.

## Files and individual commands

| File | Purpose |
| --- | --- |
| `get_data.py` | Generate raw observations without engineered features |
| `transform_features.py` | Transform raw data and save the prepared Feast source |
| `feature_repo/definitions.py` | Define one entity, source, and feature view |
| `feature_repo/feature_store.yaml` | Configure local storage |
| `common.py` | Available features, each model's subset, and store location |
| `train_models.py` | Retrieve each feature subset and train the corresponding model |
| `materialize.py` | Copy latest features into SQLite |
| `predict.py` | Retrieve features and predict with both models |
| `run_demo.py` | Run these steps in order |
| `teaching_demo.ipynb` | Guided beginner walkthrough |
| `app.py` | Optional FastAPI example |
| `verify_demo.py` | Optional instructor correctness check |

With `.venv` activated, from `feature_store_feast`, the steps are:

```powershell
python get_data.py
python transform_features.py
Push-Location feature_repo
feast apply
Pop-Location
python train_models.py
python materialize.py
python predict.py
```

Optional instructor check: `python verify_demo.py`. It checks the raw-to-prepared
pipeline, historical age values, model-specific feature subsets, latest online
values, and both models' predictions.

Tested with Python 3.11 and Feast 0.67.0. Feast requires pandas below 3, so
installing requirements may downgrade pandas in the existing `.venv`.

For further reading: [Feast feature views](https://docs.feast.dev/getting-started/concepts/feature-view)
and [online storage](https://docs.feast.dev/getting-started/components/online-store).
