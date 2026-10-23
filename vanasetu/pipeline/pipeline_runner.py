"""
VanaSetu Pipeline Runner
========================
Coordinates ingestion jobs across Sentinel-2 satellite indices, meteorological
telemetry, and active fire alerts. Identifies at-risk parcels experiencing
statistically anomalous decline and queues them for multi-agent triage.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from vanasetu.models import PlantationParcel, VegetationReading, WeatherMetrics, FireDetection
from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.tools.weather_tool import WeatherTool
from vanasetu.tools.fire_tool import FireTool
from vanasetu.pipeline.satellite_ingest import SatelliteIngestionJob
from vanasetu.pipeline.weather_ingest import WeatherIngestionJob
from vanasetu.pipeline.fire_ingest import FireIngestionJob

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    End-to-end telemetry ingestion and anomaly screening pipeline.
    """

    def __init__(
        self,
        bq_tool: Optional[BigQueryTool] = None,
        weather_tool: Optional[WeatherTool] = None,
        fire_tool: Optional[FireTool] = None,
    ):
        self.bq_tool = bq_tool or BigQueryTool()
        self.weather_tool = weather_tool or WeatherTool()
        self.fire_tool = fire_tool or FireTool()

        self.satellite_job = SatelliteIngestionJob()
        self.weather_job = WeatherIngestionJob(self.weather_tool)
        self.fire_job = FireIngestionJob(self.fire_tool)

    def run_daily_monitoring(self) -> Dict[str, Any]:
        """
        Executes daily monitoring cycle:
        1. Queries all monitored plantation parcels from BigQuery.
        2. Evaluates latest satellite vegetation telemetry.
        3. Identifies parcels with statistically significant NDVI anomalies.
        4. Gathers paired weather and fire context for anomalous parcels.
        5. Returns a structured triage queue for multi-agent analysis.
        """
        parcels = self.bq_tool.list_parcels()
        logger.info(f"Running daily monitoring across {len(parcels)} plantation parcels.")

        triage_queue: List[Dict[str, Any]] = []
        normal_parcels: List[str] = []

        for parcel in parcels:
            latest_telemetry = self.bq_tool.get_latest_vegetation(parcel.parcel_id)
            if not latest_telemetry:
                continue

            # Check if anomalous decline is detected
            if latest_telemetry.is_anomaly:
                weather = self.weather_job.process_parcel_weather(parcel)
                fires = self.fire_job.process_parcel_fires(parcel)

                triage_queue.append({
                    "parcel": parcel,
                    "telemetry": latest_telemetry,
                    "weather": weather,
                    "fires": fires,
                })
            else:
                normal_parcels.append(parcel.parcel_id)

        return {
            "total_parcels_monitored": len(parcels),
            "normal_count": len(normal_parcels),
            "anomalous_count": len(triage_queue),
            "at_risk_queue": triage_queue,
        }
