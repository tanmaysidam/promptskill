"""
VanaSetu Fire Ingestion Job
===========================
Ingests active fire detections from NASA FIRMS (VIIRS/MODIS) and ISRO Bhuvan,
computes geodesic distances to all monitored plantation parcel centroids,
and flags threatened parcels within the perimeter buffer.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Tuple
from vanasetu.models import FireDetection, PlantationParcel
from vanasetu.tools.fire_tool import FireTool, haversine_distance_km

logger = logging.getLogger(__name__)


class FireIngestionJob:
    """
    Ingests and spatially joins active fire telemetry with plantation boundaries.
    """

    def __init__(self, fire_tool: Optional[FireTool] = None, buffer_km: float = 3.0):
        self.fire_tool = fire_tool or FireTool(default_buffer_km=buffer_km)
        self.buffer_km = buffer_km

    def process_parcel_fires(
        self,
        parcel: PlantationParcel,
        raw_fire_detections: Optional[List[Dict]] = None,
    ) -> List[FireDetection]:
        """
        Calculates distances for all fires and filters those within the perimeter buffer.
        """
        if raw_fire_detections:
            processed = []
            for item in raw_fire_detections:
                dist = haversine_distance_km(
                    parcel.latitude, parcel.longitude, item["latitude"], item["longitude"]
                )
                processed.append(
                    FireDetection(
                        fire_id=item["fire_id"],
                        latitude=item["latitude"],
                        longitude=item["longitude"],
                        detected_at=item["detected_at"],
                        satellite_sensor=item.get("satellite_sensor", "VIIRS-SNPP"),
                        confidence_pct=item["confidence_pct"],
                        brightness_temp_k=item.get("brightness_temp_k", 330.0),
                        frp_mw=item.get("frp_mw", 10.0),
                        distance_km=round(dist, 2),
                        within_buffer=dist <= self.buffer_km,
                    )
                )
            return processed

        return self.fire_tool.get_nearby_fires(parcel, buffer_km=self.buffer_km)
