"""
VanaSetu Policy Verifier
========================
Executes deterministic policy rules against proposed agent diagnoses.
Acts as a strict guardrail against hallucinated causes, costly false alarms,
and unverified field dispatch.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    GroundReport,
    DiagnosisResult,
    VerificationResult,
    CauseCategory,
)
from vanasetu.policy.rules import (
    PolicyRule,
    DroughtSanityRule,
    FireEvidenceRule,
    CloudShadowRule,
    DeciduousPhenologyRule,
    BudgetEscalationRule,
)

logger = logging.getLogger(__name__)


class PolicyVerifier:
    """
    Main verifier engine that checks AI agent reasoning against
    deterministic ecological, meteorological, and budgetary rules.
    """

    def __init__(self, rules: Optional[List[PolicyRule]] = None):
        self.rules: List[PolicyRule] = rules or [
            CloudShadowRule(),
            DeciduousPhenologyRule(),
            DroughtSanityRule(),
            FireEvidenceRule(),
            BudgetEscalationRule(),
        ]

    def add_rule(self, rule: PolicyRule) -> None:
        """Appends a custom policy rule to the verification chain."""
        self.rules.append(rule)

    def verify(
        self,
        parcel: PlantationParcel,
        telemetry: Optional[VegetationReading],
        weather: Optional[WeatherMetrics],
        fires: List[FireDetection],
        ground_report: Optional[GroundReport],
        diagnosis: DiagnosisResult,
    ) -> VerificationResult:
        """
        Runs all rules and synthesizes a deterministic verification result.
        """
        passed_rules: List[str] = []
        violated_rules: List[str] = []
        explanations: List[str] = []
        overridden_cause: Optional[CauseCategory] = None
        dfo_approval_required: bool = False

        is_valid = True

        for rule in self.rules:
            rule_passed, reason, override, req_dfo = rule.evaluate(
                parcel=parcel,
                telemetry=telemetry,
                weather=weather,
                fires=fires,
                ground_report=ground_report,
                diagnosis=diagnosis,
            )

            if req_dfo:
                dfo_approval_required = True

            if override:
                overridden_cause = override

            if rule_passed:
                passed_rules.append(rule.rule_name)
                explanations.append(f"[{rule.rule_name}] PASS: {reason}")
            else:
                is_valid = False
                violated_rules.append(rule.rule_name)
                explanations.append(f"[{rule.rule_name}] VIOLATION: {reason}")

        # If overridden to a benign cause (e.g. cloud artifact or phenology), consider it valid under the new cause
        if overridden_cause in [CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM, CauseCategory.PHENOLOGICAL_SHEDDING]:
            is_valid = True

        summary_text = "\n".join(explanations)
        return VerificationResult(
            is_valid=is_valid,
            passed_rules=passed_rules,
            violated_rules=violated_rules,
            explanation=summary_text,
            overridden_cause=overridden_cause,
            dfo_approval_required=dfo_approval_required,
        )
