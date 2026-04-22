FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# curl needed for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium + all system deps (must run as root)
RUN playwright install chromium \
    && playwright install-deps chromium \
    && chmod -R a+rX /ms-playwright

# Create non-root user
RUN useradd -m -u 1000 appuser

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

USER appuser

EXPOSE 7878

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:7878/ > /dev/null || exit 1

# 1 worker + 4 threads: keeps _current_proc global consistent,
# enough concurrency for SSE + config endpoints.
# timeout=0 prevents gunicorn from killing long-running SSE streams.
CMD ["gunicorn", \
     "--workers=1", \
     "--threads=4", \
     "--timeout=0", \
     "--bind=0.0.0.0:7878", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "app:app"]
