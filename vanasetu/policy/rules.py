"""
VanaSetu Deterministic Policy Rules
===================================
Encodes biological, physical, meteorological, and administrative invariants
to verify and constrain AI agent diagnostic outputs before any work order
can be issued to a field forest crew.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from datetime import datetime

from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    GroundReport,
    DiagnosisResult,
    CauseCategory,
    UrgencyLevel,
)


class PolicyRule(ABC):
    """Abstract Base Class for deterministic verifier rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Name of the policy rule."""
        pass

    @abstractmethod
    def evaluate(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> Tuple[bool, str, Optional[CauseCategory], bool]:
        """
        Evaluates the diagnosis against domain invariants.

        Returns:
            passed (bool): True if invariant holds, False if violated.
            explanation (str): Reason for pass or violation.
            override_cause (Optional[CauseCategory]): Corrected cause if rule overrides.
            dfo_approval_required (bool): Whether this rule mandates DFO sign-off.
        """
        pass


class DroughtSanityRule(PolicyRule):
    """
    Enforces that DROUGHT_STRESS cannot be diagnosed if there has been substantial
    recent precipitation (e.g. > 25mm in past 7 days) or consecutive dry days < 5.
    Prevents LLM hallucination of drought during or immediately after rainfall.
    """

    @property
    def rule_name(self) -> str:
        return "DROUGHT_SANITY_RULE"

    def evaluate(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> Tuple[bool, str, Optional[CauseCategory], bool]:
        if diagnosis.primary_cause != CauseCategory.DROUGHT_STRESS:
            return True, "Diagnosis is not drought stress; rule passed.", None, False

        if weather is None:
            return False, "Drought stress claimed but no weather data available.", None, False

        # Invariant 1: 7-day cumulative rainfall > 25.0 mm contradicts drought stress
        if weather.precipitation_mm_7d > 25.0:
            return (
                False,
                f"Violation: Drought diagnosed, but parcel received {weather.precipitation_mm_7d}mm of rain in the last 7 days (> 25mm threshold).",
                None,
                False,
            )

        # Invariant 2: Consecutive dry days must be >= 5
        if weather.consecutive_dry_days < 5:
            return (
                False,
                f"Violation: Drought diagnosed, but consecutive dry days is only {weather.consecutive_dry_days} (< 5 days threshold).",
                None,
                False,
            )

        return (
            True,
            f"Drought confirmed: {weather.consecutive_dry_days} consecutive dry days, 7d precip {weather.precipitation_mm_7d}mm, deficit {weather.rainfall_deficit_pct}%.",
            None,
            False,
        )


class FireEvidenceRule(PolicyRule):
    """
    Enforces that SURFACE_FIRE_SCORCH cannot be claimed without empirical
    satellite thermal anomaly evidence (NASA FIRMS / VIIRS / MODIS) within 3.0km
    and confidence >= 50%.
    """

    @property
    def rule_name(self) -> str:
        return "FIRE_EVIDENCE_RULE"

    def evaluate(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> Tuple[bool, str, Optional[CauseCategory], bool]:
        if diagnosis.primary_cause != CauseCategory.SURFACE_FIRE_SCORCH:
            return True, "Diagnosis is not fire scorch; rule passed.", None, False

        # Check for matching fire detections
        valid_fires = [f for f in fires if f.within_buffer and f.confidence_pct >= 50.0]

        if not valid_fires:
            return (
                False,
                "Violation: Surface fire diagnosed, but no active thermal anomaly with >=50% confidence found within 3.0km buffer.",
                None,
                False,
            )

        best_fire = min(valid_fires, key=lambda f: f.distance_km)
        return (
            True,
            f"Fire confirmed: {best_fire.satellite_sensor} detected thermal anomaly at {best_fire.distance_km:.2f}km with {best_fire.confidence_pct}% confidence (FRP: {best_fire.frp_mw}MW).",
            None,
            False,
        )


class CloudShadowRule(PolicyRule):
    """
    Suppresses false vegetation drop alarms when satellite scene cloud cover is high (> 30%).
    Overrides diagnosis to SENSOR_ARTIFACT_FALSE_ALARM to prevent spurious dispatch.
    """

    @property
    def rule_name(self) -> str:
        return "CLOUD_SHADOW_ARTIFACT_RULE"

    def evaluate(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> Tuple[bool, str, Optional[CauseCategory], bool]:
        if telemetry is None:
            return True, "No telemetry to check for cloud artifact.", None, False

        # High cloud cover over parcel scene
        if telemetry.cloud_cover_pct >= 30.0:
            msg = (
                f"Cloud interference detected: Scene has {telemetry.cloud_cover_pct}% cloud cover. "
                f"Sudden NDVI drop ({telemetry.ndvi_drop_pct}%) is likely cloud/shadow artifact. Overriding to SENSOR_ARTIFACT_FALSE_ALARM."
            )
            return True, msg, CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM, False

        return True, f"Clean satellite observation (cloud cover {telemetry.cloud_cover_pct}% < 30%).", None, False


class DeciduousPhenologyRule(PolicyRule):
    """
    Prevents false alarms for deciduous species (e.g. Teak, Sal, Mahua) in Central/Peninsular India
    that naturally shed leaves during February-April dry months.
    """

    @property
    def rule_name(self) -> str:
        return "DECIDUOUS_PHENOLOGY_RULE"

    def evaluate(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> Tuple[bool, str, Optional[CauseCategory], bool]:
        # Calculate deciduous fraction of parcel species mix
        total_saplings = sum(s.count for s in parcel.species_mix) or 1
        deciduous_count = sum(s.count for s in parcel.species_mix if s.is_deciduous)
        deciduous_fraction = deciduous_count / total_saplings

        # Check observation month from telemetry or weather, falling back to current system month
        obs_month = None
        if telemetry and telemetry.timestamp:
            try:
                # e.g. "2024-03-20T10:30:00Z"
                date_part = telemetry.timestamp.split("T")[0]
                obs_month = int(date_part.split("-")[1])
            except Exception:
                pass
        if obs_month is None and weather and weather.observation_date:
            try:
                obs_month = int(weather.observation_date.split("-")[1])
            except Exception:
                pass
        if obs_month is None:
            obs_month = datetime.now().month

        # If stand is predominantly deciduous (> 50%) and in shedding season (Feb to April = months 2, 3, 4)
        if deciduous_fraction >= 0.50 and obs_month in [2, 3, 4]:
            # If weather is not catastrophic (rainfall deficit normal for dry season, no heatwave)
            if weather and not weather.heatwave_alert and weather.rainfall_deficit_pct < 85.0:
                if diagnosis.primary_cause in [CauseCategory.DROUGHT_STRESS, CauseCategory.PEST_OUTBREAK]:
                    msg = (
                        f"Phenology override: Stand is {deciduous_fraction*100:.0f}% deciduous (e.g. Teak/Sal). "
                        f"NDVI drop in month {obs_month} corresponds to natural seasonal leaf-fall. Overriding to PHENOLOGICAL_SHEDDING."
                    )
                    return True, msg, CauseCategory.PHENOLOGICAL_SHEDDING, False

        return True, "Phenology check passed.", None, False


class BudgetEscalationRule(PolicyRule):
    """
    Enforces governance: Any emergency intervention costing > ₹15,000 INR
    requires authorization by the Divisional Forest Officer (DFO).
    """

    @property
    def rule_name(self) -> str:
        return "BUDGET_ESCALATION_RULE"

    def evaluate(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> Tuple[bool, str, Optional[CauseCategory], bool]:
        cost = diagnosis.estimated_cost_inr

        # Baseline cost check for heavy equipment
        if cost > 15000.0:
            return (
                True,
                f"Expenditure INR ₹{cost:,.2f} exceeds ₹15,000 threshold. Mandating Divisional Forest Officer (DFO) approval.",
                None,
                True,
            )

        return True, f"Expenditure INR ₹{cost:,.2f} within beat-level discretionary authority.", None, False
