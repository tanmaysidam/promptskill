"""
VanaSetu Multi-Agent Coordinator
================================
Coordinates the end-to-end early warning and intervention lifecycle:
Sentinel Triage -> Multi-Modal Diagnosis -> Deterministic Verification -> Field Action Dispatch.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List

from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    GroundReport,
    DiagnosisResult,
    VerificationResult,
    WorkOrder,
    WorkOrderStatus,
    UrgencyLevel,
)
from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.tools.weather_tool import WeatherTool
from vanasetu.tools.fire_tool import FireTool
from vanasetu.tools.ground_report_tool import GroundReportTool
from vanasetu.policy.verifier import PolicyVerifier
from vanasetu.agents.triage_agent import SentinelTriageAgent
from vanasetu.agents.diagnosis_agent import DiagnosisAgent
from vanasetu.agents.action_agent import FieldActionAgent

logger = logging.getLogger(__name__)


class VanaSetuCoordinator:
    """
    Master coordinator orchestrating ADK agents, tools, and deterministic policy verifier.
    """

    def __init__(
        self,
        bq_tool: Optional[BigQueryTool] = None,
        weather_tool: Optional[WeatherTool] = None,
        fire_tool: Optional[FireTool] = None,
        ground_tool: Optional[GroundReportTool] = None,
        verifier: Optional[PolicyVerifier] = None,
    ):
        self.bq_tool = bq_tool or BigQueryTool()
        self.weather_tool = weather_tool or WeatherTool()
        self.fire_tool = fire_tool or FireTool()
        self.ground_tool = ground_tool or GroundReportTool()
        self.verifier = verifier or PolicyVerifier()

        # ADK Agents
        self.triage_agent = SentinelTriageAgent()
        self.diagnosis_agent = DiagnosisAgent()
        self.action_agent = FieldActionAgent()

    def process_parcel_alert(
        self,
        parcel_id: str,
        custom_telemetry: Optional[VegetationReading] = None,
        custom_weather: Optional[WeatherMetrics] = None,
        custom_fires: Optional[List[FireDetection]] = None,
        custom_ground: Optional[GroundReport] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full early-warning assessment pipeline on a single plantation parcel.
        """
        # Step 1: Query Parcel Metadata
        parcel = self.bq_tool.get_parcel(parcel_id)
        if not parcel:
            raise ValueError(f"Parcel ID {parcel_id} not found in BigQuery registry.")

        # Step 2: Fetch Multi-Modal Telemetry Streams
        telemetry = custom_telemetry or self.bq_tool.get_latest_vegetation(parcel_id)
        weather = custom_weather or self.weather_tool.get_weather_metrics(parcel)
        fires = custom_fires if custom_fires is not None else self.fire_tool.get_nearby_fires(parcel)
        ground_report = custom_ground or self.ground_tool.get_latest_ground_report(parcel_id)

        # Step 3: Run Sentinel Triage Agent
        if telemetry:
            triage_result = self.triage_agent.triage_parcel(parcel, telemetry)
        else:
            triage_result = {
                "parcel_id": parcel_id,
                "urgency": UrgencyLevel.LOW,
                "escalate_to_diagnosis": False,
                "cloud_interference": False,
                "triage_summary": "No telemetry reading available.",
            }

        # Step 4: Run Diagnostic Reasoning Agent (if escalated or active fire present)
        should_diagnose = (
            triage_result.get("escalate_to_diagnosis", False)
            or bool(fires)
            or (telemetry and telemetry.is_anomaly)
        )

        diagnosis: Optional[DiagnosisResult] = None
        verification: Optional[VerificationResult] = None
        work_order: Optional[WorkOrder] = None

        if should_diagnose:
            diagnosis = self.diagnosis_agent.diagnose_parcel(
                parcel=parcel,
                telemetry=telemetry,
                weather=weather,
                fires=fires,
                ground_report=ground_report,
                triage_urgency=triage_result.get("urgency", UrgencyLevel.HIGH),
            )

            # Step 5: Deterministic Policy Verifier (Safety & Sanity Guardrails)
            verification = self.verifier.verify(
                parcel=parcel,
                telemetry=telemetry,
                weather=weather,
                fires=fires,
                ground_report=ground_report,
                diagnosis=diagnosis,
            )

            # Step 6: Field Action Agent (Synthesize Bilingual Work Order)
            work_order = self.action_agent.generate_work_order(
                parcel=parcel,
                diagnosis=diagnosis,
                verification=verification,
            )

            # Step 7: Persist Work Order to BigQuery
            self.bq_tool.save_work_order(work_order)

        return {
            "parcel": parcel,
            "telemetry": telemetry,
            "weather": weather,
            "fires": fires,
            "ground_report": ground_report,
            "triage": triage_result,
            "diagnosis": diagnosis,
            "verification": verification,
            "work_order": work_order,
        }
