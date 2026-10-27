"""Airflow 3 TaskFlow demo: reproducible house-price retraining with quality gate."""
from datetime import timedelta
from pathlib import Path
import json
import os
import shutil

import pendulum
from airflow.sdk import dag, task, get_current_context

ROOT = Path('/opt/airflow/ml_artifacts')
FEATURES = ['area_sqft', 'bedrooms', 'age_years', 'distance_to_city_km']

@dag(
    dag_id='house_price_ml_pipeline',
    description='Synthetic housing data -> validation -> preprocessing -> training -> evaluation -> gated registration',
    start_date=pendulum.datetime(2026, 1, 1, tz='UTC'),
    schedule=None,  # Switch to '@weekly' once students understand manual triggers.
    catchup=False,  # Airflow will not automatically create historical scheduled runs that were missed.
    max_active_runs=1,
    tags=['mlops', 'teaching', 'house-prices'], # Helps users organize and find DAGs.
)
def house_price_ml_pipeline():
    @task(retries=2, retry_delay=timedelta(seconds=20))
    def generate_data() -> str:
        import numpy as np
        import pandas as pd

        run_id = get_current_context()['run_id']

        # Keep each DAG run isolated; run_id is safely mapped to an opaque path.
        from hashlib import sha256

        run_dir = ROOT / 'runs' / sha256(run_id.encode()).hexdigest()[:16]
        run_dir.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(42)
        n = 500
        area = rng.integers(500, 4000, n)
        bedrooms = rng.integers(1, 6, n)
        age = rng.integers(0, 35, n)
        distance = rng.uniform(1, 30, n).round(2)
        price = (12 + 0.035 * area + 5.0 * bedrooms - 0.30 * age - 0.8 * distance
                 + rng.normal(0, 7, n))
        price = np.maximum(price, 5.0) # ensures that the generated property prices are at least 5 lakh.

        df = pd.DataFrame({'area_sqft': area, 'bedrooms': bedrooms,
                           'age_years': age, 'distance_to_city_km': distance,
                           'price_lakhs': price.round(2)})
        
        path = run_dir / 'housing.csv'
        df.to_csv(path, index=False)
        print('Created dataset:', path, '| rows:', len(df))

        return str(path)

    @task(retries=1)
    def validate_data(csv_path: str) -> str:
        import pandas as pd

        df = pd.read_csv(csv_path)

        required = FEATURES + ['price_lakhs']

        assert len(df) >= 100, 'Insufficient training data'
        assert set(required).issubset(df.columns), 'Missing columns'
        assert not df[required].isna().any().any(), 'Missing values found'
        assert (df['area_sqft'] > 0).all(), 'Invalid area values'
        assert (df['price_lakhs'] > 0).all(), 'Invalid target values'
        assert not df.duplicated().any(), 'Duplicate rows found'

        print('Validation passed:', len(df), 'records')
        return csv_path

    @task
    def preprocess_data(csv_path: str) -> dict:
        import pandas as pd
        from sklearn.model_selection import train_test_split

        df = pd.read_csv(csv_path)
        train, test = train_test_split(df, test_size=0.2, random_state=42)
        folder = Path(csv_path).parent
        train_path, test_path = folder / 'train.csv', folder / 'test.csv'
        train.to_csv(train_path, index=False)
        test.to_csv(test_path, index=False)
        print('Split:', len(train), 'train /', len(test), 'test')
        return {'train_path': str(train_path), 'test_path': str(test_path)}

    @task
    def train_model(paths: dict) -> dict:
        import pandas as pd
        import joblib
        from sklearn.ensemble import RandomForestRegressor

        train = pd.read_csv(paths['train_path'])
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1)
        model.fit(train[FEATURES], train['price_lakhs'])
        model_path = Path(paths['train_path']).parent / 'candidate_model.joblib'
        joblib.dump(model, model_path)
        print('Candidate model:', model_path)

        return {'model_path': str(model_path), 'test_path': paths['test_path']}

    @task
    def evaluate_model(artifacts: dict) -> dict:
        import joblib
        import pandas as pd
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        test = pd.read_csv(artifacts['test_path'])
        model = joblib.load(artifacts['model_path'])
        y_pred = model.predict(test[FEATURES])
        metrics = {
            'MAE_lakhs': round(float(mean_absolute_error(test['price_lakhs'], y_pred)), 3),
            'RMSE_lakhs': round(float(mean_squared_error(test['price_lakhs'], y_pred)**0.5), 3),
            'R2': round(float(r2_score(test['price_lakhs'], y_pred)), 4),
        }

        metrics_path = Path(artifacts['model_path']).parent / 'metrics.json'
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding='utf-8')

        print('Evaluation:', metrics)
        return {'model_path': artifacts['model_path'], 'metrics_path': str(metrics_path), **metrics}

    @task
    def register_approved_model(result: dict) -> str:
        # This intentionally fails the task if model quality is unacceptable.
        # In a production system the approval and registry operations would be more sophisticated.
        if result['R2'] < 0.90 or result['MAE_lakhs'] > 15:
            raise ValueError(f"Quality gate rejected candidate: {result}")
        
        approved = ROOT / 'approved'
        approved.mkdir(parents=True, exist_ok=True)
        shutil.copy2(result['model_path'], approved / 'house_price_model.joblib')
        shutil.copy2(result['metrics_path'], approved / 'metrics.json')

        print('APPROVED MODEL:', approved / 'house_price_model.joblib')
        return str(approved / 'house_price_model.joblib')

    # Create DAG dependencies by passing the output of one task into the next:
    source = generate_data()
    validated = validate_data(source)
    paths = preprocess_data(validated)
    candidate = train_model(paths)
    metrics = evaluate_model(candidate)
    register_approved_model(metrics)



house_price_ml_pipeline()
