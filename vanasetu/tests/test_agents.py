"""
Unit Tests for VanaSetu ADK Agents
==================================
Tests SentinelTriageAgent, DiagnosisAgent, and FieldActionAgent.
"""

import pytest
from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    GroundReport,
    DiagnosisResult,
    VerificationResult,
    CauseCategory,
    UrgencyLevel,
)
from vanasetu.agents.triage_agent import SentinelTriageAgent
from vanasetu.agents.diagnosis_agent import DiagnosisAgent
from vanasetu.agents.action_agent import FieldActionAgent


@pytest.fixture
def sample_parcel():
    return BigQueryTool().get_parcel("MH-YTL-2024-001")


def test_sentinel_triage_agent_critical(sample_parcel):
    agent = SentinelTriageAgent()
    telemetry = VegetationReading(
        parcel_id=sample_parcel.parcel_id,
        timestamp="2024-08-01T10:30:00Z",
        ndvi=0.38,
        ndwi=0.12,
        cloud_cover_pct=2.0,
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=34.5,
        z_score=5.0,
        is_anomaly=True,
    )
    result = agent.triage_parcel(sample_parcel, telemetry)
    assert result["urgency"] == UrgencyLevel.CRITICAL
    assert result["escalate_to_diagnosis"] is True
    assert result["cloud_interference"] is False


def test_sentinel_triage_agent_cloud_filtering(sample_parcel):
    agent = SentinelTriageAgent()
    telemetry = VegetationReading(
        parcel_id=sample_parcel.parcel_id,
        timestamp="2024-08-01T10:30:00Z",
        ndvi=0.38,
        ndwi=0.12,
        cloud_cover_pct=45.0,  # High clouds
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=34.5,
        z_score=5.0,
        is_anomaly=True,
    )
    result = agent.triage_parcel(sample_parcel, telemetry)
    assert result["cloud_interference"] is True
    assert result["urgency"] == UrgencyLevel.INFO


def test_diagnosis_agent_fire_priority(sample_parcel):
    agent = DiagnosisAgent()
    fires = [
        FireDetection(
            fire_id="F1",
            latitude=sample_parcel.latitude + 0.005,
            longitude=sample_parcel.longitude + 0.005,
            detected_at="2024-08-01T12:00:00Z",
            confidence_pct=88.0,
            brightness_temp_k=340.0,
            frp_mw=15.0,
            distance_km=0.75,
            within_buffer=True,
        )
    ]
    diag = agent.diagnose_parcel(
        parcel=sample_parcel,
        telemetry=None,
        weather=None,
        fires=fires,
        ground_report=None,
    )
    assert diag.primary_cause == CauseCategory.SURFACE_FIRE_SCORCH
    assert diag.urgency == UrgencyLevel.CRITICAL
    assert diag.confidence_score >= 0.85


def test_diagnosis_agent_drought(sample_parcel):
    agent = DiagnosisAgent()
    weather = WeatherMetrics(
        parcel_id=sample_parcel.parcel_id,
        observation_date="2024-08-01",
        precipitation_mm_7d=0.0,
        precipitation_mm_14d=1.5,
        precipitation_mm_30d=12.0,
        rainfall_deficit_pct=82.0,
        max_temperature_c=41.2,
        consecutive_dry_days=22,
        vapor_pressure_deficit_kpa=3.6,
        heatwave_alert=True,
    )
    telemetry = VegetationReading(
        parcel_id=sample_parcel.parcel_id,
        timestamp="2024-08-01T10:30:00Z",
        ndvi=0.42,
        ndwi=0.11,
        cloud_cover_pct=3.0,
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=27.5,
        z_score=4.0,
        is_anomaly=True,
    )
    diag = agent.diagnose_parcel(
        parcel=sample_parcel,
        telemetry=telemetry,
        weather=weather,
        fires=[],
        ground_report=None,
    )
    assert diag.primary_cause == CauseCategory.DROUGHT_STRESS
    assert diag.urgency == UrgencyLevel.CRITICAL


def test_field_action_agent(sample_parcel):
    agent = FieldActionAgent()
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.INVASIVE_WEED_CHOKING,
        confidence_score=0.91,
        urgency=UrgencyLevel.HIGH,
        reasoning_summary="Severe weed competition",
    )
    verification = VerificationResult(
        is_valid=True,
        passed_rules=["ALL_CLEAR"],
        violated_rules=[],
        explanation="Verified",
    )

    wo = agent.generate_work_order(sample_parcel, diagnosis, verification)
    assert wo.parcel_id == sample_parcel.parcel_id
    assert "INVASIVE WEED REMOVAL" in wo.crew_instructions_en
    assert "खरपतवार नियंत्रण" in wo.crew_instructions_hi
    assert len(wo.required_equipment) > 0
