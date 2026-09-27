# Build from the backend/ directory:
#   docker build -t tenderextractor-backend ./backend
# Run:
#   docker run -p 8000:8000 --env-file .env \
#     -v tenderextractor_data:/app/data_uploads \
#     -v tenderextractor_output:/app/output \
#     -v tenderextractor_logs:/app/logs \
#     tenderextractor-backend
#
# data_uploads/ holds the source PDFs, output/ the generated Excel files,
# and logs/ app.log - mount volumes over all three (as above) or the
# container loses them on every restart/redeploy. local_state/ (the
# SQLite job store, config.JOBS_DB) is deliberately NOT mounted - it must
# stay on local disk since SQLite doesn't work reliably over network
# filesystems like Azure Files; run with minReplicas >= 1 in production
# if you don't want job history reset on every scale-to-zero cycle. The
# pipeline also pushes a copy of that SQLite file to Blob Storage after
# every run (job_db_backup.py) when AZURE_STORAGE_CONNECTION_STRING is
# set, so job history stays reachable even without the volume.

FROM python:3.11-slim

WORKDIR /app

# Install from the pinned lock file (not requirements.txt) for reproducible
# builds - regenerate requirements.lock.txt when requirements.txt changes
# (see the comment at the top of that file). Its own layer so `docker
# build` only re-runs pip install when it actually changes, not on every
# code edit.
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY app ./app
COPY main.py .
COPY scripts ./scripts

# Placeholders so the app doesn't need to mkdir at first request; real
# deployments should mount volumes over these (see docker run example above).
RUN mkdir -p data_uploads output logs local_state

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Single worker is plenty for a single-user tool; job status/tokens/etc.
# persist to SQLite either way, so bumping --workers later is safe if you
# ever need it.
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
