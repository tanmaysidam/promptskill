"""
VanaSetu Sentinel Triage Agent
==============================
ADK Agent responsible for screening incoming satellite vegetation anomalies,
evaluating cloud interference, assessing decline severity, and assigning initial
triage priority.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    UrgencyLevel,
)
from vanasetu.agents.adk_base import ADKAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the Sentinel Triage Agent of VanaSetu, India's AI early-warning system for plantation sapling monitoring.
Your duty is to evaluate incoming Sentinel-2 vegetation anomaly alerts across plantation parcels.
You analyze NDVI drop percentage, NDWI canopy moisture loss, scene cloud contamination, and historical statistical z-scores.
Your output determines if an alert requires full diagnostic escalation or can be dismissed as benign / sensor artifact.
"""


class SentinelTriageAgent(ADKAgent):
    """
    Screens satellite telemetry alerts and triages parcels for diagnostic intervention.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        super().__init__(
            name="SentinelTriageAgent",
            role_description="Screens satellite telemetry alerts and assigns triage urgency.",
            system_instruction=SYSTEM_PROMPT,
            model_name=model_name,
        )

    def triage_parcel(
        self,
        parcel: PlantationParcel,
        telemetry: VegetationReading,
    ) -> Dict[str, Any]:
        """
        Evaluates parcel vegetation status and determines triage priority.
        """
        # Formulate prompt for LLM if live client available
        prompt = (
            f"Analyze satellite reading for Parcel {parcel.parcel_id} ({parcel.forest_division}, {parcel.state}):\n"
            f"- Current NDVI: {telemetry.ndvi:.3f} (Baseline Mean: {telemetry.baseline_ndvi_mean:.3f}, Drop: {telemetry.ndvi_drop_pct}%)\n"
            f"- Current NDWI: {telemetry.ndwi:.3f}\n"
            f"- Cloud Cover: {telemetry.cloud_cover_pct}%\n"
            f"- Anomaly Z-Score: {telemetry.z_score}\n"
            f"Determine triage urgency (CRITICAL, HIGH, MEDIUM, LOW, INFO) and justification."
        )

        llm_response = self.run_llm_call(prompt)

        # Deterministic ADK reasoning logic
        cloud_flag = telemetry.cloud_cover_pct >= 30.0

        if cloud_flag:
            urgency = UrgencyLevel.INFO
            action_required = False
            summary = (
                f"Triage: Scene has {telemetry.cloud_cover_pct}% cloud contamination. "
                f"NDVI drop of {telemetry.ndvi_drop_pct}% is suspected cloud shadow artifact. Queued for multi-pass confirmation."
            )
        elif telemetry.ndvi_drop_pct >= 30.0 or telemetry.z_score >= 3.5:
            urgency = UrgencyLevel.CRITICAL
            action_required = True
            summary = (
                f"Triage CRITICAL: Severe vegetation collapse detected! NDVI dropped by {telemetry.ndvi_drop_pct}% "
                f"(Z-score: {telemetry.z_score}). Immediate diagnostic multi-modal investigation required."
            )
        elif telemetry.ndvi_drop_pct >= 20.0 or telemetry.z_score >= 2.5:
            urgency = UrgencyLevel.HIGH
            action_required = True
            summary = (
                f"Triage HIGH: Significant vegetation stress detected. NDVI drop {telemetry.ndvi_drop_pct}% "
                f"with NDWI decline to {telemetry.ndwi:.3f}. Escalating to diagnostic investigation."
            )
        elif telemetry.ndvi_drop_pct >= 12.0 or telemetry.z_score >= 1.8:
            urgency = UrgencyLevel.MEDIUM
            action_required = True
            summary = (
                f"Triage MEDIUM: Moderate vegetation anomaly. NDVI drop {telemetry.ndvi_drop_pct}%. "
                f"Escalating for preventive cross-correlation."
            )
        else:
            urgency = UrgencyLevel.LOW
            action_required = False
            summary = f"Triage LOW: Vegetation decline {telemetry.ndvi_drop_pct}% within standard seasonal variance."

        return {
            "parcel_id": parcel.parcel_id,
            "urgency": urgency,
            "escalate_to_diagnosis": action_required,
            "cloud_interference": cloud_flag,
            "triage_summary": summary,
            "llm_output": llm_response,
        }
