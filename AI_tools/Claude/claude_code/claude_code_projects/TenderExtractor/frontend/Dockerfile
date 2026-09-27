# Build from the frontend/ directory:
#   docker build -t tenderextractor-frontend ./frontend
# Run (point it at wherever the backend container/service is reachable):
#   docker run -p 8501:8501 -e TENDEREXTRACTOR_API_URL=http://backend:8000 \
#     tenderextractor-frontend
#
# This image never sees Azure keys, JWT secrets, or the database - it's a
# pure HTTP client of the backend API (see streamlit_app.py), so it only
# needs to know where that API is.

FROM python:3.11-slim

WORKDIR /app

# Install from the pinned lock file (not requirements.txt) for reproducible
# builds - regenerate requirements.lock.txt when requirements.txt changes
# (see the comment at the top of that file).
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY streamlit_app.py .

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)" || exit 1

CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
