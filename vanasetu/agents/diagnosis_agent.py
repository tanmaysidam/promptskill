"""
VanaSetu Diagnosis Agent
========================
ADK Agent responsible for multi-modal ecological and causal diagnosis.
Synthesizes satellite Earth observation, IMD meteorological drought telemetry,
NASA FIRMS active fire hotspots, and forest ranger ground-truth surveys.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
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
from vanasetu.agents.adk_base import ADKAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the Chief Ecological Diagnostic Agent of VanaSetu.
Your mission is to perform comprehensive causal diagnosis on declining forest restoration parcels in India.
You receive:
1. Parcel metadata (location, plantation scheme, species mix, soil type, irrigation, fencing).
2. Satellite spectral telemetry (NDVI drop, NDWI moisture index, cloud cover, z-score).
3. Meteorological telemetry (consecutive dry days, 7d/14d/30d rainfall deficit, temperature, VPD).
4. Active thermal detections (NASA FIRMS / VIIRS fire hotspots, distance, FRP, confidence).
5. Ground ranger survey logs (sapling mortality, cattle grazing tracks, weed overgrowth, fence integrity).

You must weigh competing hypotheses:
- DROUGHT_STRESS: prolonged dry spells, severe rainfall deficit, high VPD, cracked soil.
- SURFACE_FIRE_SCORCH: active fire detection within buffer, charred ground, rapid drop.
- INVASIVE_WEED_CHOKING: dense Lantana camara / weed overgrowth, good soil moisture, slow canopy smothering.
- GRAZING_DAMAGE: fence breached, cattle/nilgai tracks, chewed terminal crowns.
- PEST_OUTBREAK: stem borer, defoliators, fungal blight symptoms.
- PHENOLOGICAL_SHEDDING: deciduous trees shedding leaves in dry season, no actual mortality.
- SENSOR_ARTIFACT_FALSE_ALARM: heavy cloud cover or shadow.
"""


class DiagnosisAgent(ADKAgent):
    """
    Performs causal reasoning across multi-modal environmental telemetry.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        super().__init__(
            name="DiagnosisAgent",
            role_description="Performs multi-modal causal diagnosis on forest degradation.",
            system_instruction=SYSTEM_PROMPT,
            model_name=model_name,
        )

    def diagnose_parcel(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        triage_urgency: UrgencyLevel = UrgencyLevel.HIGH,
    ) -> DiagnosisResult:
        """
        Executes causal reasoning to determine the root cause of plantation decline.
        """
        # 1. Check for Active Fire Threat
        close_fires = [f for f in fires if f.within_buffer and f.confidence_pct >= 50.0]
        if close_fires:
            f = min(close_fires, key=lambda x: x.distance_km)
            return DiagnosisResult(
                parcel_id=parcel.parcel_id,
                primary_cause=CauseCategory.SURFACE_FIRE_SCORCH,
                confidence_score=round(min(0.98, f.confidence_pct / 100.0), 2),
                urgency=UrgencyLevel.CRITICAL,
                reasoning_summary=(
                    f"Thermal anomaly detected by {f.satellite_sensor} at distance {f.distance_km:.2f}km "
                    f"from parcel centroid with {f.confidence_pct}% confidence (FRP: {f.frp_mw}MW). "
                    f"Indicates active forest surface burn or escaped crop stubble fire threatening plantation boundaries."
                ),
                supporting_evidence=[
                    f"Thermal hotspot {f.fire_id} within {f.distance_km:.2f}km buffer zone.",
                    f"Fire Radiative Power: {f.frp_mw} MW, Brightness Temp: {f.brightness_temp_k} K.",
                    f"Vegetation NDVI drop: {telemetry.ndvi_drop_pct if telemetry else 'N/A'}%.",
                ],
                conflicting_signals=[],
                proposed_actions=[
                    "Deploy forest fire squad immediately with backpack mist extinguishers and fire rakes.",
                    "Carve a 5-meter wide cleared fire break line along the active perimeter.",
                    "Douse smoldering leaf litter and protect sapling root collars.",
                ],
                estimated_cost_inr=parcel.area_hectares * 4000.0,
            )

        # 2. Check for Cloud Shadow / Sensor Artifact
        if telemetry and telemetry.cloud_cover_pct >= 30.0:
            return DiagnosisResult(
                parcel_id=parcel.parcel_id,
                primary_cause=CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM,
                confidence_score=0.92,
                urgency=UrgencyLevel.LOW,
                reasoning_summary=(
                    f"Satellite scene has {telemetry.cloud_cover_pct}% cloud contamination. "
                    f"The apparent NDVI drop of {telemetry.ndvi_drop_pct}% is attributable to cloud shadow interference, "
                    f"not real biological sapling mortality."
                ),
                supporting_evidence=[
                    f"Cloud cover {telemetry.cloud_cover_pct}% exceeds 30% tolerance threshold.",
                    f"Recent precipitation {weather.precipitation_mm_7d if weather else 'N/A'}mm indicates active monsoon cloudiness.",
                ],
                conflicting_signals=["Single-pass NDVI drop looks sharp but unverified under clear skies."],
                proposed_actions=["Queue parcel for clear-sky Sentinel-2 pass verification. No field dispatch needed."],
                estimated_cost_inr=0.0,
            )

        # 3. Check for Deciduous Phenology (e.g. Teak, Sal in dry season)
        total_saplings = sum(s.count for s in parcel.species_mix) or 1
        deciduous_count = sum(s.count for s in parcel.species_mix if s.is_deciduous)
        deciduous_pct = (deciduous_count / total_saplings) * 100.0
        # Determine observation month from telemetry or weather
        obs_month = None
        if telemetry and telemetry.timestamp:
            try:
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

        if deciduous_pct >= 50.0 and obs_month in [2, 3, 4] and (not weather or weather.rainfall_deficit_pct < 85.0):
            # Check if ground report confirms healthy dormant trees without high mortality
            if not ground_report or ground_report.sapling_mortality_est_pct < 15.0:
                return DiagnosisResult(
                    parcel_id=parcel.parcel_id,
                    primary_cause=CauseCategory.PHENOLOGICAL_SHEDDING,
                    confidence_score=0.88,
                    urgency=UrgencyLevel.LOW,
                    reasoning_summary=(
                        f"Plantation is {deciduous_pct:.0f}% deciduous species ({', '.join(s.common_name for s in parcel.species_mix if s.is_deciduous)}). "
                        f"Vegetation index drop of {telemetry.ndvi_drop_pct if telemetry else 0}% in month {obs_month} is consistent "
                        f"with natural seasonal leaf-shedding (phenology) typical of Central Indian dry deciduous forests."
                    ),
                    supporting_evidence=[
                        f"Stand composition is predominantly deciduous ({deciduous_pct:.0f}%).",
                        f"Observation month {obs_month} falls inside the standard dry-season leaf drop window.",
                    ],
                    conflicting_signals=[],
                    proposed_actions=["Continue routine summer fire patrolling. Withhold emergency watering."],
                    estimated_cost_inr=0.0,
                )

        # 4. Check Ground Report Evidence (Grazing / Weed Choking / Pests)
        if ground_report:
            # Check cattle grazing / fence breach
            if "breach" in ground_report.fence_condition.lower() or "cattle" in ground_report.grazing_damage.lower():
                return DiagnosisResult(
                    parcel_id=parcel.parcel_id,
                    primary_cause=CauseCategory.GRAZING_DAMAGE,
                    confidence_score=0.94,
                    urgency=UrgencyLevel.HIGH,
                    reasoning_summary=(
                        f"Ground survey by {ground_report.ranger_name} confirms perimeter fence breach ({ground_report.fence_condition}) "
                        f"and active cattle / wildlife browsing. Sapling mortality estimated at {ground_report.sapling_mortality_est_pct}% "
                        f"due to trampled crowns and severed terminal shoots."
                    ),
                    supporting_evidence=[
                        f"Field Ranger Report: {ground_report.raw_notes}",
                        f"Grazing observations: {ground_report.grazing_damage}",
                        f"Fence status: {ground_report.fence_condition}",
                    ],
                    conflicting_signals=[],
                    proposed_actions=[
                        "Mobilize fence repair squad with replacement high-tensile wire and solar energizer testing.",
                        "Deepen cattle-proof trenches along vulnerable perimeter.",
                        "Coordinate with local Vana Samiti / Gram Panchayat to prevent livestock grazing.",
                    ],
                    estimated_cost_inr=parcel.area_hectares * 2500.0,
                )

            # Check invasive weed choking (e.g. Lantana camara)
            if "severe" in ground_report.weed_infestation.lower() or "lantana" in ground_report.weed_infestation.lower():
                return DiagnosisResult(
                    parcel_id=parcel.parcel_id,
                    primary_cause=CauseCategory.INVASIVE_WEED_CHOKING,
                    confidence_score=0.91,
                    urgency=UrgencyLevel.HIGH,
                    reasoning_summary=(
                        f"Ground survey confirms severe invasive weed infestation ({ground_report.weed_infestation}). "
                        f"Aggressive Lantana camara / alien weeds are smothering sapling canopies, depriving them of sunlight "
                        f"and outcompeting for soil moisture despite adequate rainfall ({weather.precipitation_mm_14d if weather else 'N/A'}mm)."
                    ),
                    supporting_evidence=[
                        f"Field Ranger Survey: {ground_report.raw_notes}",
                        f"Soil moisture reported as {ground_report.soil_moisture_visual}.",
                        f"NDVI drop {telemetry.ndvi_drop_pct if telemetry else 'N/A'}% reflects canopy suppression.",
                    ],
                    conflicting_signals=["Soil moisture is adequate, ruling out meteorological drought."],
                    proposed_actions=[
                        "Organize community Vana Samiti weed eradication drive.",
                        "Manually uproot Lantana rootstock within 1.5m radius of all planted saplings.",
                        "Erect bamboo stakes for suppressed native saplings.",
                    ],
                    estimated_cost_inr=parcel.area_hectares * 4500.0,
                )

        # 5. Check Meteorological Drought Stress
        if weather and (weather.consecutive_dry_days >= 12 or weather.rainfall_deficit_pct >= 50.0):
            urgency = UrgencyLevel.CRITICAL if (weather.consecutive_dry_days >= 18 or weather.heatwave_alert) else UrgencyLevel.HIGH
            return DiagnosisResult(
                parcel_id=parcel.parcel_id,
                primary_cause=CauseCategory.DROUGHT_STRESS,
                confidence_score=0.93,
                urgency=urgency,
                reasoning_summary=(
                    f"Severe soil moisture deficit and meteorological drought identified. "
                    f"Parcel has experienced {weather.consecutive_dry_days} consecutive dry days with a 14-day rainfall deficit of {weather.rainfall_deficit_pct}%. "
                    f"Elevated Vapor Pressure Deficit ({weather.vapor_pressure_deficit_kpa} kPa) and max temperature ({weather.max_temperature_c}°C) "
                    f"have induced acute canopy desiccation in {parcel.soil_type} soil."
                ),
                supporting_evidence=[
                    f"Consecutive dry days: {weather.consecutive_dry_days} (Threshold >= 12).",
                    f"7-day cumulative rainfall: {weather.precipitation_mm_7d} mm.",
                    f"Atmospheric evaporative demand (VPD): {weather.vapor_pressure_deficit_kpa} kPa.",
                    f"Satellite NDWI moisture collapse to {telemetry.ndwi if telemetry else 'low'}.",
                ],
                conflicting_signals=[],
                proposed_actions=[
                    "Dispatch emergency tractor water bowser (5000L) for deep saucer-basin watering (15L/sapling).",
                    "Apply organic straw/husk mulching around root collars to reduce evaporation.",
                    "Excavate contour bund micro-catchments to harvest any upcoming shower.",
                ],
                estimated_cost_inr=(parcel.area_hectares * 3500.0) + 5000.0,
            )

        # 6. Default fallback / Unknown
        return DiagnosisResult(
            parcel_id=parcel.parcel_id,
            primary_cause=CauseCategory.UNKNOWN,
            confidence_score=0.50,
            urgency=triage_urgency,
            reasoning_summary=(
                f"Vegetation decline observed (NDVI drop {telemetry.ndvi_drop_pct if telemetry else 'N/A'}%), "
                f"but multi-modal signals do not conclusively isolate a single stressor. Field verification required."
            ),
            supporting_evidence=[],
            conflicting_signals=["Weather and satellite signals inconclusive."],
            proposed_actions=["Dispatch beat guard for on-ground physical inspection and mobile report filing."],
            estimated_cost_inr=parcel.area_hectares * 800.0,
        )
