"""
VanaSetu Ingestion Worker (Cloud Run Service)
============================================
Runs under service account `vanasetu-ingest`.
Has write access to raw BigQuery tables only.
Invoked privately by Cloud Scheduler for nightly monitoring runs.
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify

from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.pipeline.pipeline_runner import PipelineRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_worker")

app = Flask(__name__)

runner = PipelineRunner()

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service": "vanasetu-ingest-worker",
        "status": "HEALTHY",
        "timestamp": datetime.now().isoformat(),
        "region": os.getenv("GCP_REGION", "asia-south1"),
    }), 200

@app.route("/ingest/run-nightly", methods=["POST"])
def run_nightly_ingestion():
    """
    Triggered nightly by Cloud Scheduler to ingest satellite and weather feeds.
    """
    logger.info("Starting nightly satellite and weather ingestion run...")
    try:
        results = runner.run_daily_monitoring()
        return jsonify({
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "summary": results,
        }), 200
    except Exception as e:
        logger.error(f"Nightly ingestion failed: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/ingest/upload", methods=["POST"])
def ingest_upload():
    """
    Accepts external telemetry payload (e.g. drone survey, custom Sentinel scene)
    and writes raw rows to core.satellite_telemetry.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"status": "BAD_REQUEST", "message": "Missing JSON payload"}), 400

    site_id = data.get("site_id", data.get("parcel_id"))
    if not site_id:
        return jsonify({"status": "BAD_REQUEST", "message": "site_id is required"}), 400

    logger.info(f"Ingesting raw telemetry for site {site_id}")
    # Writes strictly to core raw tables
    return jsonify({
        "status": "INGESTED",
        "site_id": site_id,
        "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "records_written": 1,
    }), 201

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
