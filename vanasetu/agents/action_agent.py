"""
VanaSetu Field Action Agent
===========================
ADK Agent that translates verified ecological diagnoses into actionable,
localized work orders for field beat guards, Van Samitis, and range officers.
Generates bilingual instructions (English and Hindi), resource allocations,
and emergency escalation flags.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from vanasetu.models import (
    PlantationParcel,
    DiagnosisResult,
    VerificationResult,
    WorkOrder,
    WorkOrderStatus,
)
from vanasetu.tools.work_order_tool import WorkOrderTool
from vanasetu.agents.adk_base import ADKAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the Field Operations Action Agent of VanaSetu.
Your mission is to formulate field-ready, practical intervention orders for Indian forest beat officers and community Vana Samitis.
You ensure that:
1. Operational instructions are crystal-clear, safe, and culturally contextualized in both English and Hindi.
2. Required equipment (bowsers, fire beaters, weed pullers, wire) is explicitly specified.
3. Person-days and budget estimates in INR comply with state forest schedule of rates (SoR).
4. If the estimated cost exceeds ₹15,000 INR, the order requires authorization by the Divisional Forest Officer (DFO).
"""


class FieldActionAgent(ADKAgent):
    """
    Translates verified diagnoses into structured, field-executable work orders.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        super().__init__(
            name="FieldActionAgent",
            role_description="Generates actionable, bilingual field intervention work orders.",
            system_instruction=SYSTEM_PROMPT,
            model_name=model_name,
        )

    def generate_work_order(
        self,
        parcel: PlantationParcel,
        diagnosis: DiagnosisResult,
        verification: VerificationResult,
    ) -> WorkOrder:
        """
        Creates a formalized, verified work order.
        """
        work_order = WorkOrderTool.create_work_order(
            parcel=parcel,
            diagnosis=diagnosis,
            verification=verification,
        )

        logger.info(
            f"Generated WorkOrder {work_order.work_order_id} for parcel {parcel.parcel_id} "
            f"| Status: {work_order.status} | Cost: INR ₹{work_order.estimated_cost_inr:,.2f}"
        )
        return work_order
