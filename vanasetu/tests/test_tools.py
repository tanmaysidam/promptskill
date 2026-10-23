"""
Unit Tests for VanaSetu Tools
=============================
Validates BigQueryTool, WeatherTool, FireTool, GroundReportTool, and WorkOrderTool.
"""

import pytest
from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.tools.weather_tool import WeatherTool
from vanasetu.tools.fire_tool import FireTool, haversine_distance_km
from vanasetu.tools.ground_report_tool import GroundReportTool
from vanasetu.tools.work_order_tool import WorkOrderTool
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


def test_bigquery_tool_parcels():
    bq = BigQueryTool()
    parcels = bq.list_parcels()
    assert len(parcels) >= 5

    p = bq.get_parcel("MH-YTL-2024-001")
    assert p is not None
    assert p.state == "Maharashtra"
    assert p.district == "Yavatmal"
    assert len(p.species_mix) > 0


def test_bigquery_vegetation_history():
    bq = BigQueryTool()
    history = bq.get_vegetation_history("MH-YTL-2024-001", limit=5)
    assert len(history) == 5
    latest = bq.get_latest_vegetation("MH-YTL-2024-001")
    assert latest is not None
    assert latest.ndvi > 0.0


def test_weather_tool_vpd_and_metrics():
    tool = WeatherTool()
    # Test VPD calculation: at 35°C, 40% RH, VPD should be around 3.3 kPa
    vpd = tool.compute_vpd(35.0, 40.0)
    assert 2.5 <= vpd <= 4.0

    p = BigQueryTool().get_parcel("MH-YTL-2024-001")
    metrics = tool.get_weather_metrics(p)
    assert metrics.parcel_id == p.parcel_id
    assert metrics.consecutive_dry_days >= 0
    assert metrics.max_temperature_c > 0


def test_fire_tool_proximity():
    tool = FireTool()
    # Distance between Mumbai (19.0760, 72.8777) and Pune (18.5204, 73.8567) is ~120km
    d = haversine_distance_km(19.0760, 72.8777, 18.5204, 73.8567)
    assert 115.0 < d < 125.0

    # Similipal buffer parcel has active fire
    p = BigQueryTool().get_parcel("OR-SMP-2024-003")
    fires = tool.get_nearby_fires(p)
    assert len(fires) > 0
    assert fires[0].within_buffer is True
    assert tool.has_active_fire_threat(p) is True


def test_ground_report_tool():
    tool = GroundReportTool()
    rep = tool.get_latest_ground_report("KA-WGH-2023-014")
    assert rep is not None
    assert "Lantana" in rep.weed_infestation


def test_work_order_tool_bilingual_and_cost():
    parcel = BigQueryTool().get_parcel("MH-YTL-2024-001")
    diagnosis = DiagnosisResult(
        parcel_id=parcel.parcel_id,
        primary_cause=CauseCategory.DROUGHT_STRESS,
        confidence_score=0.92,
        urgency=UrgencyLevel.CRITICAL,
        reasoning_summary="Severe drought stress in black cotton soil.",
        proposed_actions=["Dispatch water tanker."],
        estimated_cost_inr=18000.0,
    )
    verification = VerificationResult(
        is_valid=True,
        passed_rules=["DROUGHT_SANITY_RULE"],
        violated_rules=[],
        explanation="Valid",
        dfo_approval_required=True,
    )

    wo = WorkOrderTool.create_work_order(parcel, diagnosis, verification)
    assert wo.parcel_id == parcel.parcel_id
    assert "EMERGENCY IRRIGATION" in wo.crew_instructions_en
    assert "आपातकालीन सिंचाई" in wo.crew_instructions_hi
    assert wo.dfo_approval_required is True
    assert wo.estimated_cost_inr > 15000.0
