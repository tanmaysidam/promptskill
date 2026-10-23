"""
VanaSetu Ground Report Tool
===========================
Ingests and retrieves field verification surveys submitted by forest beat guards,
field foresters, and village Vana Samitis (Joint Forest Management Committees).
Captures sapling mortality counts, fence integrity, weed choking, and cattle grazing tracks.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from vanasetu.models import GroundReport, PlantationParcel

logger = logging.getLogger(__name__)


class GroundReportTool:
    """
    Manages ground-truth survey reports from forest rangers and field crews.
    Connects with mobile survey tools (ODK Collect / Bhuvan App / KoboToolbox).
    """

    def __init__(self):
        self._reports: Dict[str, List[GroundReport]] = {}
        self._scenario_overrides: Dict[str, GroundReport] = {}
        self._seed_default_reports()

    def _seed_default_reports(self) -> None:
        """Seeds realistic historical survey logs for sample parcels."""
        now = datetime.now()
        # Kudremukh Western Ghats parcel: heavy Lantana weed choking reported
        self._reports["KA-WGH-2023-014"] = [
            GroundReport(
                report_id="GR-WGH-2024-001",
                parcel_id="KA-WGH-2023-014",
                survey_date=(now - timedelta(days=4)).strftime("%Y-%m-%d"),
                ranger_name="Naveen Kumar",
                ranger_id="FR-KA-4412",
                sapling_mortality_est_pct=18.0,
                soil_moisture_visual="Adequate",
                pest_symptoms="None",
                weed_infestation="Severe - Lantana / invasive choking",
                grazing_damage="None",
                fence_condition="Intact",
                raw_notes="Severe Lantana camara and bracken fern overgrowth smothering 1-year-old Jamun and Dalchini saplings. Sunlight completely blocked from reaching ground canopy. Urgent manual uprooting needed.",
            )
        ]

        # Adilabad parcel: Solar fence breached by cattle
        self._reports["TS-ADB-2024-009"] = [
            GroundReport(
                report_id="GR-ADB-2024-008",
                parcel_id="TS-ADB-2024-009",
                survey_date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
                ranger_name="K. Srinivas",
                ranger_id="FSO-TS-109",
                sapling_mortality_est_pct=25.0,
                soil_moisture_visual="Adequate",
                pest_symptoms="None",
                weed_infestation="Low",
                grazing_damage="Active cattle browsing and trampled crowns",
                fence_condition="Breached",
                raw_notes="South-eastern perimeter solar electric wire broken by fallen branch. Local village cattle entered overnight. Terminal shoots of young Bijasal saplings eaten; extensive hoof trampling.",
            )
        ]

    def set_scenario_override(self, parcel_id: str, report: GroundReport) -> None:
        """Injects a specific ground report scenario."""
        self._scenario_overrides[parcel_id] = report

    def clear_overrides(self) -> None:
        """Clears all scenario overrides."""
        self._scenario_overrides.clear()

    def get_latest_ground_report(self, parcel_id: str) -> Optional[GroundReport]:
        """Fetches the most recent ground survey filed for this parcel."""
        if parcel_id in self._scenario_overrides:
            return self._scenario_overrides[parcel_id]

        reports = self._reports.get(parcel_id, [])
        return reports[-1] if reports else None

    def submit_ground_report(self, report: GroundReport) -> bool:
        """Records a new field ground survey."""
        if report.parcel_id not in self._reports:
            self._reports[report.parcel_id] = []
        self._reports[report.parcel_id].append(report)
        logger.info(f"Recorded ground report {report.report_id} for parcel {report.parcel_id}")
        return True
