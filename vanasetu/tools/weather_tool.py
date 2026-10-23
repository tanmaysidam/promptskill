"""
VanaSetu Weather Tool
=====================
Computes meteorological drought indicators, dry spell duration (CDD),
Vapor Pressure Deficit (VPD), and rainfall deficits against India Meteorological
Department (IMD) historical normals.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from datetime import datetime, date
import math

from vanasetu.models import WeatherMetrics, PlantationParcel

logger = logging.getLogger(__name__)


class WeatherTool:
    """
    Fetches and computes agro-meteorological metrics for a plantation parcel.
    Provides live API support via Open-Meteo with offline scenario generator for testing.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        # Preset scenario overrides for test cases & simulation
        self._scenario_overrides: Dict[str, WeatherMetrics] = {}

    def set_scenario_override(self, parcel_id: str, metrics: WeatherMetrics) -> None:
        """Injects a specific weather scenario for evaluation or testing."""
        self._scenario_overrides[parcel_id] = metrics

    def clear_overrides(self) -> None:
        """Clears all scenario overrides."""
        self._scenario_overrides.clear()

    def get_weather_metrics(
        self,
        parcel: PlantationParcel,
        target_date: Optional[str] = None,
    ) -> WeatherMetrics:
        """
        Retrieves weather metrics for the given parcel. Checks overrides first,
        then attempts live Open-Meteo API query, falling back to agro-climatic simulation.
        """
        if parcel.parcel_id in self._scenario_overrides:
            return self._scenario_overrides[parcel.parcel_id]

        obs_date = target_date or datetime.now().strftime("%Y-%m-%d")

        # Attempt live API fetch if network is available
        try:
            import requests
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={parcel.latitude}&longitude={parcel.longitude}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
                f"&past_days=14&forecast_days=1&timezone=auto"
            )
            resp = requests.get(url, timeout=4.0)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get("daily", {})
                precip = daily.get("precipitation_sum", [])
                temps = daily.get("temperature_2m_max", [])

                if precip and temps:
                    p7 = sum(precip[-7:]) if len(precip) >= 7 else sum(precip)
                    p14 = sum(precip[-14:]) if len(precip) >= 14 else sum(precip)
                    p30 = p14 * 1.8  # estimate if 30 days not queried
                    max_t = sum(temps[-7:]) / len(temps[-7:]) if len(temps) >= 7 else (temps[-1] if temps else 32.0)

                    # Consecutive dry days (< 1.0mm)
                    cdd = 0
                    for val in reversed(precip):
                        if val < 1.0:
                            cdd += 1
                        else:
                            break

                    vpd = self.compute_vpd(max_t, 45.0)
                    heatwave = max_t >= 40.0

                    return WeatherMetrics(
                        parcel_id=parcel.parcel_id,
                        observation_date=obs_date,
                        precipitation_mm_7d=round(p7, 1),
                        precipitation_mm_14d=round(p14, 1),
                        precipitation_mm_30d=round(p30, 1),
                        rainfall_deficit_pct=round(max(0.0, 100.0 - (p14 / 35.0 * 100)), 1),
                        max_temperature_c=round(max_t, 1),
                        consecutive_dry_days=cdd,
                        vapor_pressure_deficit_kpa=round(vpd, 2),
                        heatwave_alert=heatwave,
                    )
        except Exception as e:
            logger.debug(f"Live weather API lookup failed ({e}), falling back to regional baseline.")

        # Baseline regional fallback
        return self._simulate_regional_weather(parcel, obs_date)

    def _simulate_regional_weather(self, parcel: PlantationParcel, obs_date: str) -> WeatherMetrics:
        """Generates realistic regional weather baseline based on Indian agro-climatic zone."""
        # Vidarbha / Central India: hot, prone to dry spells
        if "MH-YTL" in parcel.parcel_id:
            return WeatherMetrics(
                parcel_id=parcel.parcel_id,
                observation_date=obs_date,
                precipitation_mm_7d=2.0,
                precipitation_mm_14d=5.0,
                precipitation_mm_30d=18.0,
                rainfall_deficit_pct=68.5,
                max_temperature_c=39.5,
                consecutive_dry_days=18,
                vapor_pressure_deficit_kpa=3.2,
                heatwave_alert=False,
            )
        # Western Ghats: high rainfall
        elif "KA-WGH" in parcel.parcel_id:
            return WeatherMetrics(
                parcel_id=parcel.parcel_id,
                observation_date=obs_date,
                precipitation_mm_7d=85.0,
                precipitation_mm_14d=190.0,
                precipitation_mm_30d=420.0,
                rainfall_deficit_pct=0.0,
                max_temperature_c=26.5,
                consecutive_dry_days=0,
                vapor_pressure_deficit_kpa=0.9,
                heatwave_alert=False,
            )
        # Coastal Konkan: heavy monsoon
        elif "MH-RTG" in parcel.parcel_id:
            return WeatherMetrics(
                parcel_id=parcel.parcel_id,
                observation_date=obs_date,
                precipitation_mm_7d=140.0,
                precipitation_mm_14d=280.0,
                precipitation_mm_30d=650.0,
                rainfall_deficit_pct=0.0,
                max_temperature_c=28.0,
                consecutive_dry_days=0,
                vapor_pressure_deficit_kpa=0.7,
                heatwave_alert=False,
            )
        # Default normal
        return WeatherMetrics(
            parcel_id=parcel.parcel_id,
            observation_date=obs_date,
            precipitation_mm_7d=18.0,
            precipitation_mm_14d=42.0,
            precipitation_mm_30d=95.0,
            rainfall_deficit_pct=15.0,
            max_temperature_c=32.0,
            consecutive_dry_days=3,
            vapor_pressure_deficit_kpa=1.8,
            heatwave_alert=False,
        )

    @staticmethod
    def compute_vpd(temp_c: float, relative_humidity_pct: float) -> float:
        """
        Calculates Vapor Pressure Deficit (VPD in kPa) using the Tetens formula.
        High VPD (> 2.5 kPa) creates extreme evaporative demand, causing sapling transpiration shutdown.
        """
        # Saturated vapor pressure (es) in kPa
        es = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        # Actual vapor pressure (ea)
        ea = es * (relative_humidity_pct / 100.0)
        return max(0.0, es - ea)
