# House Price MLOps Airflow Demo (Airflow 3.3.2)

## Prerequisites
Windows 11, Docker Desktop running Linux containers, Docker Compose v2, 4 GB+ Docker memory (8 GB recommended).

## Setup (PowerShell in this folder)
1. Download the official Airflow Compose configuration:
   `Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/3.3.2/docker-compose.yaml" -OutFile "docker-compose.yaml"`
2. Create folders: `New-Item -ItemType Directory -Force dags,logs,plugins,config,ml_artifacts | Out-Null`
3. Build the teaching image: `docker build -t house-price-airflow:3.3.2 .`
4. Initialize services: `docker compose up airflow-init`
5. Start in background: `docker compose up -d`
6. Visit http://localhost:8080 — username and password: `airflow` / `airflow` (teaching configuration only).
7. Find `house_price_ml_pipeline` and trigger it manually.
8. Explore the DAG's Graph view, each task log, and the XCom outputs. On success inspect `ml_artifacts/approved/metrics.json` and `ml_artifacts/approved/house_price_model.joblib`.
9. Shut down: `docker compose down` (preserves stored data). Avoid `-v` unless you intend to remove database volumes.

## Teaching exercises
- **Dependencies**: TaskFlow creates dependencies from the outputs passed to downstream functions.
- **Retry**: In `generate_data`, temporarily add `raise RuntimeError('Simulated failure')`. Observe retries and logs; then remove it and rerun.
- **Data validation**: Change `area` generation from a positive range to negative values. Observe the downstream tasks not starting.
- **Quality gate**: Change `R2 < 0.90` to `R2 < 0.99999`. Observe that training and evaluation succeed while registration fails.
- **Schedule**: Change `schedule=None` to `schedule='@weekly'` to enable periodic DAG runs (plus unpause in UI). Keep `catchup=False`.
- **XCom**: Examine returned small dictionaries/paths. Large CSV datasets and model binaries are kept on disk, NOT XCom.

## Notes
- The `ml_artifacts` bind mount is added only to `airflow-worker`, where tasks execute in the official CeleryExecutor starter configuration.
- Files for separate DAG runs use separate hashed directories. The `approved` folder is overwritten only after a candidate passes the quality gate.
- This is for learning, not a secure or hardened production deployment.
- In real deployments use object storage such as S3, a model registry like MLflow, a production secrets manager, model lineage, data versioning, proper observability and concurrent-safe promotion.
