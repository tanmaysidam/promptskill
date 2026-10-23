"""
End-to-End Integration Tests for VanaSetu
=========================================
Tests the complete multi-agent workflow from satellite telemetry ingestion,
triage, diagnosis, deterministic policy verification, work order generation,
and BigQuery persistence.
"""

import pytest
from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    GroundReport,
    CauseCategory,
    WorkOrderStatus,
    UrgencyLevel,
)
from vanasetu.agents.coordinator import VanaSetuCoordinator


def test_coordinator_end_to_end_drought_scenario():
    coordinator = VanaSetuCoordinator()
    parcel_id = "MH-YTL-2024-001"

    custom_telemetry = VegetationReading(
        parcel_id=parcel_id,
        timestamp="2024-08-01T10:30:00Z",
        ndvi=0.42,
        ndwi=0.12,
        evi=0.36,
        cloud_cover_pct=3.0,
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=27.59,
        z_score=4.0,
        is_anomaly=True,
    )
    custom_weather = WeatherMetrics(
        parcel_id=parcel_id,
        observation_date="2024-08-01",
        precipitation_mm_7d=1.0,
        precipitation_mm_14d=3.0,
        precipitation_mm_30d=14.0,
        rainfall_deficit_pct=75.0,
        max_temperature_c=40.2,
        consecutive_dry_days=21,
        vapor_pressure_deficit_kpa=3.5,
        heatwave_alert=False,
    )

    result = coordinator.process_parcel_alert(
        parcel_id=parcel_id,
        custom_telemetry=custom_telemetry,
        custom_weather=custom_weather,
        custom_fires=[],
        custom_ground=None,
    )

    # 1. Verify Triage
    assert result["triage"]["escalate_to_diagnosis"] is True
    assert result["triage"]["urgency"] in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]

    # 2. Verify Diagnosis
    diagnosis = result["diagnosis"]
    assert diagnosis is not None
    assert diagnosis.primary_cause == CauseCategory.DROUGHT_STRESS

    # 3. Verify Deterministic Verification
    verification = result["verification"]
    assert verification is not None
    assert verification.is_valid is True
    assert "DROUGHT_SANITY_RULE" in verification.passed_rules
    assert verification.dfo_approval_required is True

    # 4. Verify Work Order
    work_order = result["work_order"]
    assert work_order is not None
    assert work_order.status == WorkOrderStatus.VERIFIED
    assert work_order.dfo_approval_required is True
    assert "EMERGENCY IRRIGATION" in work_order.crew_instructions_en
    assert "आपातकालीन सिंचाई" in work_order.crew_instructions_hi

    # 5. Verify Persistence in BigQuery Store
    saved_orders = coordinator.bq_tool.list_work_orders(parcel_id)
    assert len(saved_orders) >= 1
    persisted = coordinator.bq_tool.get_work_order(work_order.work_order_id)
    assert persisted is not None
    assert persisted.work_order_id == work_order.work_order_id


def test_coordinator_cloud_shadow_false_alarm_suppression():
    coordinator = VanaSetuCoordinator()
    parcel_id = "MH-RTG-2024-022"

    # Cloud shadow simulation
    telemetry = VegetationReading(
        parcel_id=parcel_id,
        timestamp="2024-07-15T10:30:00Z",
        ndvi=0.38,
        ndwi=0.48,
        cloud_cover_pct=48.0,  # Heavy cloud cover
        baseline_ndvi_mean=0.58,
        baseline_ndvi_std=0.04,
        ndvi_drop_pct=34.48,
        z_score=5.0,
        is_anomaly=True,
    )

    result = coordinator.process_parcel_alert(
        parcel_id=parcel_id,
        custom_telemetry=telemetry,
    )

    # Verifier must intercept and override to SENSOR_ARTIFACT_FALSE_ALARM
    work_order = result["work_order"]
    assert work_order is not None
    assert work_order.diagnosed_cause == CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM
    # Field dispatch is suppressed / zero cost
    assert work_order.estimated_cost_inr == 0.0
    assert work_order.estimated_person_days == 1 or "cloud" in work_order.crew_instructions_en.lower()
