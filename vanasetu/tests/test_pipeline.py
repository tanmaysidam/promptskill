"""
Unit Tests for VanaSetu Ingestion Pipeline
=========================================
Tests satellite, weather, and fire ingestion jobs and the pipeline runner.
"""

import pytest
from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.pipeline.satellite_ingest import SatelliteIngestionJob
from vanasetu.pipeline.weather_ingest import WeatherIngestionJob
from vanasetu.pipeline.fire_ingest import FireIngestionJob
from vanasetu.pipeline.pipeline_runner import PipelineRunner


def test_satellite_ingest_anomaly_detection():
    job = SatelliteIngestionJob(anomaly_drop_threshold_pct=15.0, z_score_threshold=2.0)
    parcel = BigQueryTool().get_parcel("MH-YTL-2024-001")

    # Baseline 0.60, current 0.42 -> drop 30%, z-score 4.5 -> Anomaly!
    drop_pct, z_score, is_anomaly = job.compute_anomaly(
        current_ndvi=0.42,
        baseline_mean=0.60,
        baseline_std=0.04,
    )
    assert drop_pct == 30.0
    assert z_score == 4.5
    assert is_anomaly is True

    # Normal variation: baseline 0.60, current 0.58 -> drop 3.3%, z-score 0.5 -> Normal
    drop_pct2, z_score2, is_anomaly2 = job.compute_anomaly(
        current_ndvi=0.58,
        baseline_mean=0.60,
        baseline_std=0.04,
    )
    assert drop_pct2 < 5.0
    assert is_anomaly2 is False

    reading = job.process_scene_observation(
        parcel=parcel,
        ndvi=0.45,
        ndwi=0.20,
        cloud_cover_pct=5.0,
        baseline_mean=0.60,
        baseline_std=0.04,
    )
    assert reading.parcel_id == parcel.parcel_id
    assert reading.ndvi_drop_pct == 25.0
    assert reading.is_anomaly is True


def test_weather_ingest_job():
    parcel = BigQueryTool().get_parcel("MH-YTL-2024-001")
    job = WeatherIngestionJob()
    metrics = job.process_parcel_weather(parcel)
    assert metrics.parcel_id == parcel.parcel_id
    assert metrics.precipitation_mm_7d >= 0.0


def test_fire_ingest_job():
    parcel = BigQueryTool().get_parcel("OR-SMP-2024-003")
    job = FireIngestionJob()
    fires = job.process_parcel_fires(parcel)
    assert len(fires) > 0
    assert fires[0].within_buffer is True


def test_pipeline_runner_execution():
    runner = PipelineRunner()
    result = runner.run_daily_monitoring()
    assert result["total_parcels_monitored"] >= 5
    assert "at_risk_queue" in result
