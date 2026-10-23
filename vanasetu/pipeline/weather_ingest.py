"""
VanaSetu Weather Ingestion Job
==============================
Aggregates daily precipitation and temperature time-series to generate
rolling 7-day, 14-day, and 30-day cumulative weather metrics, consecutive dry days (CDD),
and Vapor Pressure Deficit (VPD).
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from vanasetu.models import WeatherMetrics, PlantationParcel
from vanasetu.tools.weather_tool import WeatherTool

logger = logging.getLogger(__name__)


class WeatherIngestionJob:
    """
    Ingests and transforms weather observations for monitored parcels.
    """

    def __init__(self, weather_tool: Optional[WeatherTool] = None):
        self.weather_tool = weather_tool or WeatherTool()

    def process_parcel_weather(
        self,
        parcel: PlantationParcel,
        target_date: Optional[str] = None,
    ) -> WeatherMetrics:
        """
        Retrieves, aggregates, and transforms weather telemetry for a parcel.
        """
        return self.weather_tool.get_weather_metrics(parcel, target_date=target_date)
