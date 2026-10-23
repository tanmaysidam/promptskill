"""
Unit Tests for VanaSetu Deterministic Policy Rules
=================================================
Tests domain invariants: drought sanity, fire evidence, cloud artifacts,
deciduous phenology, and budget escalation thresholds.
"""

import pytest
from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    DiagnosisResult,
    CauseCategory,
    UrgencyLevel,
)
from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.policy.rules import (
    DroughtSanityRule,
    FireEvidenceRule,
    CloudShadowRule,
    DeciduousPhenologyRule,
    BudgetEscalationRule,
)
from vanasetu.policy.verifier import PolicyVerifier


@pytest.fixture
def sample_parcel():
    return BigQueryTool().get_parcel("MH-YTL-2024-001")


def test_drought_sanity_rule_violation_on_rain(sample_parcel):
    rule = DroughtSanityRule()
    # High rainfall in past 7 days (40mm > 25mm threshold)
    weather = WeatherMetrics(
        parcel_id=sample_parcel.parcel_id,
        observation_date="2024-08-01",
        precipitation_mm_7d=40.0,
        precipitation_mm_14d=90.0,
        precipitation_mm_30d=180.0,
        rainfall_deficit_pct=0.0,
        max_temperature_c=29.0,
        consecutive_dry_days=1,
        vapor_pressure_deficit_kpa=1.0,
    )
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.DROUGHT_STRESS,
        confidence_score=0.9,
        urgency=UrgencyLevel.HIGH,
        reasoning_summary="Hallucinated drought during heavy rain",
    )

    passed, reason, override, req_dfo = rule.evaluate(
        parcel=sample_parcel,
        telemetry=None,
        weather=weather,
        fires=[],
        ground_report=None,
        diagnosis=diagnosis,
    )
    assert passed is False
    assert "Violation" in reason
    assert "40.0mm" in reason


def test_drought_sanity_rule_pass_on_dry_spell(sample_parcel):
    rule = DroughtSanityRule()
    weather = WeatherMetrics(
        parcel_id=sample_parcel.parcel_id,
        observation_date="2024-08-01",
        precipitation_mm_7d=0.0,
        precipitation_mm_14d=2.0,
        precipitation_mm_30d=15.0,
        rainfall_deficit_pct=80.0,
        max_temperature_c=41.0,
        consecutive_dry_days=18,
        vapor_pressure_deficit_kpa=3.5,
    )
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.DROUGHT_STRESS,
        confidence_score=0.95,
        urgency=UrgencyLevel.CRITICAL,
        reasoning_summary="Genuine drought",
    )

    passed, reason, override, req_dfo = rule.evaluate(
        parcel=sample_parcel,
        telemetry=None,
        weather=weather,
        fires=[],
        ground_report=None,
        diagnosis=diagnosis,
    )
    assert passed is True
    assert "Drought confirmed" in reason


def test_fire_evidence_rule_without_thermal_detection(sample_parcel):
    rule = FireEvidenceRule()
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.SURFACE_FIRE_SCORCH,
        confidence_score=0.85,
        urgency=UrgencyLevel.CRITICAL,
        reasoning_summary="Fire diagnosed without thermal sensor hotspot",
    )

    passed, reason, override, req_dfo = rule.evaluate(
        parcel=sample_parcel,
        telemetry=None,
        weather=None,
        fires=[],  # No active fires
        ground_report=None,
        diagnosis=diagnosis,
    )
    assert passed is False
    assert "no active thermal anomaly" in reason


def test_cloud_shadow_override(sample_parcel):
    rule = CloudShadowRule()
    telemetry = VegetationReading(
        parcel_id=sample_parcel.parcel_id,
        timestamp="2024-07-20T10:30:00Z",
        ndvi=0.35,
        ndwi=0.45,
        cloud_cover_pct=45.0,  # High cloud cover
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=39.0,
        z_score=5.7,
        is_anomaly=True,
    )
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.DROUGHT_STRESS,
        confidence_score=0.8,
        urgency=UrgencyLevel.HIGH,
        reasoning_summary="Apparent NDVI collapse",
    )

    passed, reason, override, req_dfo = rule.evaluate(
        parcel=sample_parcel,
        telemetry=telemetry,
        weather=None,
        fires=[],
        ground_report=None,
        diagnosis=diagnosis,
    )
    assert passed is True
    assert override == CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM


def test_budget_escalation_rule(sample_parcel):
    rule = BudgetEscalationRule()
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.DROUGHT_STRESS,
        confidence_score=0.9,
        urgency=UrgencyLevel.CRITICAL,
        reasoning_summary="High cost water tanker operation",
        estimated_cost_inr=24000.0,  # Exceeds ₹15,000 threshold
    )

    passed, reason, override, req_dfo = rule.evaluate(
        parcel=sample_parcel,
        telemetry=None,
        weather=None,
        fires=[],
        ground_report=None,
        diagnosis=diagnosis,
    )
    assert passed is True
    assert req_dfo is True
    assert "exceeds ₹15,000 threshold" in reason


def test_policy_verifier_end_to_end(sample_parcel):
    verifier = PolicyVerifier()
    telemetry = VegetationReading(
        parcel_id=sample_parcel.parcel_id,
        timestamp="2024-08-01T10:30:00Z",
        ndvi=0.42,
        ndwi=0.15,
        cloud_cover_pct=5.0,
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=27.5,
        z_score=4.0,
        is_anomaly=True,
    )
    weather = WeatherMetrics(
        parcel_id=sample_parcel.parcel_id,
        observation_date="2024-08-01",
        precipitation_mm_7d=0.0,
        precipitation_mm_14d=2.0,
        precipitation_mm_30d=12.0,
        rainfall_deficit_pct=85.0,
        max_temperature_c=40.5,
        consecutive_dry_days=20,
        vapor_pressure_deficit_kpa=3.6,
    )
    diagnosis = DiagnosisResult(
        parcel_id=sample_parcel.parcel_id,
        primary_cause=CauseCategory.DROUGHT_STRESS,
        confidence_score=0.94,
        urgency=UrgencyLevel.CRITICAL,
        reasoning_summary="Legitimate acute drought stress",
        estimated_cost_inr=18500.0,
    )

    res = verifier.verify(
        parcel=sample_parcel,
        telemetry=telemetry,
        weather=weather,
        fires=[],
        ground_report=None,
        diagnosis=diagnosis,
    )
    assert res.is_valid is True
    assert "DROUGHT_SANITY_RULE" in res.passed_rules
    assert res.dfo_approval_required is True
