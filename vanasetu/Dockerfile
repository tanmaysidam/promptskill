FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn flask

COPY . /app/vanasetu
ENV PYTHONPATH=/app

EXPOSE 8080

# Default entrypoint runs ingest worker, can be overridden by Cloud Run args for dispatch worker
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 120 vanasetu.pipeline.ingest_worker:app
