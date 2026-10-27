# Feast: reusable housing features from notebook to API

This local teaching demo generates synthetic house sales, prepares features once,
and trains **Ridge regression and Random Forest regression** from the same Feast
feature views. Both estimate the next day's sale price in synthetic USD. No
external dataset, Docker, cloud account, or credentials are needed.

## Run using the existing virtual environment

From `C:\Users\Ash\Desktop\educational\play_ML` in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r feature_store_feast/requirements.txt
python feature_store_feast/run_demo.py
```

If PowerShell blocks activation, use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r feature_store_feast/requirements.txt
.\.venv\Scripts\python.exe feature_store_feast/run_demo.py
```

The runner generates data, prepares features, applies Feast definitions, trains
both models, materializes features into SQLite, and runs verification checks.
It prints test MAE/RMSE (lower is better), example predictions, and a PASS message.
Run it again to regenerate the demo relative to today's UTC date. A fixed seed
gives reproducible random draws; dates and age features follow the current date.
Generated files are deliberately ignored by Git.

## Teach with the notebook

Open `teaching_demo.ipynb` in Jupyter or VS Code, select the existing `.venv`
Python kernel, and run cells in order. The notebook exposes the same reusable
Python functions used by scripts. It does not contain a second copy of feature
engineering logic. It works with the notebook directory or project root as the
working directory. The script runner is also usable without Jupyter installed.

Suggested lesson sequence:

1. Inspect raw houses, sales, and labels. Discuss why two notebooks independently
   calculating neighborhood prices can disagree about windows or timestamps.
2. Run `build_features.py`: calculate and persist the shared transformations once.
3. Inspect the two entities, two feature views, and two feature services. Register
   the contracts with `feast apply`.
4. Retrieve a historical dataframe with Feast and inspect the rolling market
   feature. Change the prediction timestamp for the same neighborhood to see it change.
5. Train both models. Each calls `get_historical_features` using its own feature
   service; an assertion proves their feature values are identical.
6. Materialize and call the API twice with the same house and different model
   choices. The response includes feature values so the reuse is visible.

## Data and feature engineering

`generate_data.py` creates 300 houses in six neighborhoods and 180 days of sales
(35 sales per day). Houses may sell repeatedly; this intentionally simplified
market produces enough history for a small classroom demo. Prices depend on
size, bedrooms, age, neighborhood, a time trend, and noise.

| Dataset | Contents |
| --- | --- |
| `houses.parquet` | House ID, neighborhood ID, area, bedrooms, year built |
| `sales.parquet` | Raw realized prices and UTC sale timestamps |
| `labels.parquet` | Next-day target price, house/neighborhood IDs, prediction timestamp |
| `house_features.parquet` | Daily snapshots of reusable property features |
| `market_features.parquet` | Daily snapshots of reusable neighborhood aggregates |

| Feature | Why it is useful |
| --- | --- |
| `area_sqft`, `bedrooms` | Strong basic price predictors |
| `log_area` | Compresses area scale for linear models |
| `area_per_bedroom` | Captures room spaciousness |
| `house_age_years` | Age at the snapshot date, rather than at training execution |
| `neighborhood_price_per_sqft_30d` | Recent local market level; changes over time |
| `neighborhood_sales_count_30d` | How much recent activity supports the aggregate |

The rolling window at timestamp **t** is **(t − 30 days, t]**. Synthetic sales
are assumed available exactly at their recorded timestamp, with no reporting lag.
Features at t predict a sale at t + 1 day. The target sale is therefore outside
its feature window. Targets stay in the label dataframe, outside Feast views.
In a real market, use actual availability times and account for reporting lag;
event timestamps alone cannot prevent leakage from late-arriving corrections.

Labels start after a 30-day warm-up. Training uses the first 80% of prediction
dates and testing uses the remaining dates, with no random split. Repeated house
IDs are intentional: this evaluates future prices for the existing population,
not generalization to entirely unseen houses. Metrics are illustrative synthetic
results, not a claim about real house-price accuracy.

## What Feast does

```text
Notebook exploration -> shared batch feature preparation -> Parquet history
                                                          |
                                      Feast registry (definitions/contracts)
                                                          |
                            +-----------------------------+------------------+
                            |                                                |
              get_historical_features                              materialize
               (point-in-time joins)                                    |
                            |                                    SQLite online store
                   Ridge + Random Forest                                 |
                                                             get_online_features
                                                                         |
                                                              FastAPI + saved model
```

Feast is a feature-management and retrieval library. It **does not automatically
engineer arbitrary raw data**. Our batch Python code prepares features; Feast
registers definitions, joins historical features, and serves materialized values.
In production, a scheduler or pipeline reruns that preparation and materialization.

- **Entity:** key identifying a house or neighborhood. The API maps a house to
  its neighborhood using trusted metadata rather than accepting a mismatched pair.
- **Feature view:** typed features, source, entity, and a two-day TTL. The house
  and market views have different entity keys and are joined into one dataframe.
- **Feature service:** named model input contract referencing existing views.
  `linear_price_v1` and `forest_price_v1` reuse the same views and all seven inputs.
  Models could select different subsets without duplicating stored features.
- **Registry:** metadata about entities, views, and services; it is not the
  offline feature data itself.
- **Offline store:** Parquet feature history queried for training/batch scoring.
- **Point-in-time join:** for each prediction row, Feast selects the newest
  snapshot at or before its timestamp and within the TTL. It must not replace
  every training row with today's market value.
  Feast 0.67's local file backend can omit rows with only expired candidates;
  the training code checks row counts as well as missing values to catch this.
- **TTL vs aggregation window:** 30 days determines the raw sales summarized;
  two days determines how far back a historical lookup may search for a snapshot.
  TTL does not schedule refreshes or guarantee online freshness.
- **Materialization:** copies the latest values per entity to the online store.
  The local SQLite store serves the latest snapshot, not historical time travel.
- **Online retrieval:** the API asks for entity IDs and model service, then
  passes returned columns in the saved training order to the saved estimator.
  It performs no duplicate feature engineering.

Shared computation and contracts reduce training/serving skew; they do not
eliminate the need for data validation, refresh schedules, and freshness monitoring.
The demo checks online/offline equality at the latest snapshot. `verify_demo.py`
also checks an older snapshot against raw trailing sales, expiration in historical
joins, successful prediction by both models, and API error responses.

## Serve predictions

After running the demo:

```powershell
cd feature_store_feast
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Visit [interactive API documentation](http://127.0.0.1:8000/docs), or run in a
second PowerShell window:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -ContentType 'application/json' -Body '{"house_id":1,"model":"linear"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -ContentType 'application/json' -Body '{"house_id":1,"model":"forest"}'
```

The response contains price, model name, and the exact retrieved feature values.
Unknown houses return 404, invalid requests 422, and missing features 503.
This is a local teaching API; online values are not automatically refreshed or
rejected for age. Regenerate and materialize before teaching on another day.

## Run individual steps

With `.venv` activated, from `feature_store_feast`:

```powershell
python generate_data.py
python build_features.py
Push-Location feature_repo
feast apply
feast feature-views list
feast feature-services list
Pop-Location
python train_models.py
python materialize.py
python verify_demo.py
```

## Files and production mapping

| File | Responsibility |
| --- | --- |
| `generate_data.py` | Synthetic raw dataset and prediction labels |
| `build_features.py` | Single shared feature preparation pipeline |
| `feature_repo/definitions.py` | Entities, views, sources, model services |
| `feature_repo/feature_store.yaml` | Local registry, file offline store, SQLite online store |
| `common.py` | Repository path, ordered model columns, service names |
| `train_models.py` | Historical retrieval, chronological evaluation, saved models/metrics |
| `materialize.py` | Latest features into online storage |
| `app.py` | Entity-key-based prediction with either saved model |
| `verify_demo.py` | Time-aware correctness and API integration checks |
| `run_demo.py` | Entire verified workflow using the current Python interpreter |
| `teaching_demo.ipynb` | Guided classroom walkthrough |

FastAPI can run in Docker or AWS while using the same Feast definitions and
model contracts. For a real deployment, replace local files/SQLite with supported
shared offline/online stores, use accessible source paths and registry storage,
schedule feature jobs, version contracts with model artifacts, and add freshness
monitoring, authentication, and deployment controls. Installing Feast alone does
not deploy a production feature platform. Local paths and SQLite are intentional
for this lesson; no cloud deployment is performed here.

Dependencies target Python 3.11 and Feast 0.67.0. Feast requires pandas below 3;
installing requirements in the shared `.venv` may downgrade an existing pandas 3.
Use only trusted local model artifacts because joblib loading executes Python.

Official references: [feature views](https://docs.feast.dev/getting-started/concepts/feature-view),
[point-in-time joins](https://docs.feast.dev/getting-started/concepts/point-in-time-joins),
[online store](https://docs.feast.dev/getting-started/components/online-store).
