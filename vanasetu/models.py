"""
VanaSetu Core Domain Data Models
================================
Defines strongly-typed Pydantic schemas for plantation parcels, telemetry
readings (satellite, weather, fire), ground survey reports, diagnostic
hypotheses, policy verification results, and field work orders.
"""

from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class UrgencyLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class CauseCategory(str, Enum):
    DROUGHT_STRESS = "DROUGHT_STRESS"
    SURFACE_FIRE_SCORCH = "SURFACE_FIRE_SCORCH"
    INVASIVE_WEED_CHOKING = "INVASIVE_WEED_CHOKING"
    GRAZING_DAMAGE = "GRAZING_DAMAGE"
    PEST_OUTBREAK = "PEST_OUTBREAK"
    PHENOLOGICAL_SHEDDING = "PHENOLOGICAL_SHEDDING"
    SENSOR_ARTIFACT_FALSE_ALARM = "SENSOR_ARTIFACT_FALSE_ALARM"
    UNKNOWN = "UNKNOWN"


class WorkOrderStatus(str, Enum):
    PROPOSED = "PROPOSED"
    VERIFIED = "VERIFIED"
    REJECTED_BY_POLICY = "REJECTED_BY_POLICY"
    DISPATCHED = "DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class SpeciesRecord(BaseModel):
    species_name: str = Field(..., description="Botanical name, e.g. Azadirachta indica")
    common_name: str = Field(..., description="Indian common name, e.g. Neem")
    count: int = Field(..., description="Number of saplings planted")
    is_deciduous: bool = Field(False, description="Whether species sheds foliage seasonally in dry season")
    drought_tolerance: str = Field("MODERATE", description="LOW, MODERATE, HIGH")


class PlantationParcel(BaseModel):
    parcel_id: str = Field(..., description="Unique parcel identifier, e.g. MH-YTL-2024-001")
    state: str = Field(..., description="Indian State, e.g. Maharashtra")
    district: str = Field(..., description="District, e.g. Yavatmal")
    forest_division: str = Field(..., description="Forest Division, e.g. Yavatmal Forest Division")
    range_name: str = Field(..., description="Forest Range")
    beat_name: str = Field(..., description="Forest Beat")
    latitude: float = Field(..., description="Centroid latitude")
    longitude: float = Field(..., description="Centroid longitude")
    area_hectares: float = Field(..., description="Plantation area in hectares")
    plantation_date: str = Field(..., description="Date of plantation (YYYY-MM-DD)")
    afforestation_scheme: str = Field("CAMPA", description="CAMPA, Green India Mission, Nagar Van, etc.")
    species_mix: List[SpeciesRecord] = Field(default_factory=list)
    soil_type: str = Field("Black Cotton", description="Soil classification")
    irrigation_type: str = Field("Rainfed", description="Rainfed, Drip, Water Bowser, Staggered Contour Trenches")
    fencing_type: str = Field("Solar Electric", description="Solar Electric, Chain-link, Barbed Wire, Cattle Trench, None")
    assigned_officer: str = Field("Beat Guard", description="Name of forest beat guard or ranger")
    officer_phone: str = Field("+91-9876543210", description="Contact phone for field dispatch")


class VegetationReading(BaseModel):
    parcel_id: str
    timestamp: str
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index (-1 to 1)")
    ndwi: float = Field(..., description="Normalized Difference Water Index (-1 to 1)")
    evi: Optional[float] = Field(None, description="Enhanced Vegetation Index")
    cloud_cover_pct: float = Field(0.0, description="Cloud cover percentage over the parcel")
    baseline_ndvi_mean: float = Field(..., description="Seasonal baseline NDVI for this parcel")
    baseline_ndvi_std: float = Field(0.05, description="Historical standard deviation of NDVI")
    ndvi_drop_pct: float = Field(0.0, description="Percentage drop relative to baseline")
    z_score: float = Field(0.0, description="Anomaly z-score relative to historical baseline")
    is_anomaly: bool = Field(False, description="Flag indicating statistically significant decline")


class WeatherMetrics(BaseModel):
    parcel_id: str
    observation_date: str
    precipitation_mm_7d: float = Field(..., description="Cumulative 7-day rainfall in mm")
    precipitation_mm_14d: float = Field(..., description="Cumulative 14-day rainfall in mm")
    precipitation_mm_30d: float = Field(..., description="Cumulative 30-day rainfall in mm")
    rainfall_deficit_pct: float = Field(0.0, description="Rainfall deficit percentage compared to IMD normals")
    max_temperature_c: float = Field(..., description="Average maximum daily temperature over last 7 days")
    consecutive_dry_days: int = Field(..., description="Consecutive days with precipitation < 1mm")
    vapor_pressure_deficit_kpa: float = Field(..., description="Vapor Pressure Deficit in kPa")
    heatwave_alert: bool = Field(False, description="IMD criteria heatwave flag")


class FireDetection(BaseModel):
    fire_id: str
    latitude: float
    longitude: float
    detected_at: str
    satellite_sensor: str = Field("VIIRS-SNPP", description="VIIRS or MODIS sensor")
    confidence_pct: float = Field(..., description="Detection confidence 0-100%")
    brightness_temp_k: float = Field(..., description="Brightness temperature in Kelvin")
    frp_mw: float = Field(..., description="Fire Radiative Power in Megawatts")
    distance_km: float = Field(..., description="Distance in km to parcel centroid")
    within_buffer: bool = Field(False, description="True if within critical buffer (<= 3.0km)")


class GroundReport(BaseModel):
    report_id: str
    parcel_id: str
    survey_date: str
    ranger_name: str
    ranger_id: str
    sapling_mortality_est_pct: float = Field(0.0, description="Visual estimate of dying or dead saplings")
    soil_moisture_visual: str = Field("Adequate", description="Saturated, Adequate, Cracked/Parched Dry")
    pest_symptoms: str = Field("None", description="Identified pest or disease symptoms")
    weed_infestation: str = Field("Low", description="Low, Moderate, Severe - Lantana / invasive choking")
    grazing_damage: str = Field("None", description="None, Trampled, Active cattle browsing")
    fence_condition: str = Field("Intact", description="Intact, Breached, Broken poles, None")
    raw_notes: str = Field("", description="Field observations in English or Hindi")


class DiagnosisResult(BaseModel):
    parcel_id: str
    primary_cause: CauseCategory
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    urgency: UrgencyLevel
    reasoning_summary: str = Field(..., description="Comprehensive chain of thought reasoning")
    supporting_evidence: List[str] = Field(default_factory=list)
    conflicting_signals: List[str] = Field(default_factory=list)
    proposed_actions: List[str] = Field(default_factory=list)
    estimated_cost_inr: float = Field(0.0, description="Estimated emergency cost in Indian Rupees")


class VerificationResult(BaseModel):
    is_valid: bool = Field(..., description="True if passes all deterministic safety & sanity rules")
    passed_rules: List[str] = Field(default_factory=list)
    violated_rules: List[str] = Field(default_factory=list)
    explanation: str = Field(..., description="Detailed explanation of verification outcome")
    overridden_cause: Optional[CauseCategory] = Field(None, description="Corrected cause if verifier overrides")
    dfo_approval_required: bool = Field(False, description="Flag if requires DFO / supervisory authorization")


class WorkOrder(BaseModel):
    work_order_id: str
    parcel_id: str
    created_at: str
    status: WorkOrderStatus = WorkOrderStatus.PROPOSED
    urgency: UrgencyLevel
    diagnosed_cause: CauseCategory
    confidence_score: float
    verification: Optional[VerificationResult] = None
    crew_instructions_en: str
    crew_instructions_hi: str
    recommended_actions: List[str] = Field(default_factory=list)
    required_equipment: List[str] = Field(default_factory=list)
    estimated_person_days: int = 1
    estimated_cost_inr: float = 0.0
    dfo_approval_required: bool = False
    assigned_beat_guard: str
    contact_phone: str
    dispatch_payload: Dict[str, Any] = Field(default_factory=dict)
