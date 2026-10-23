"""
VanaSetu Evaluation Harness
===========================
Executes historical restoration test cases against the multi-agent system
and deterministic policy verifier. Computes accuracy, policy adherence,
false alarm suppression, and operational latency.
"""

from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

from vanasetu.models import (
    PlantationParcel,
    VegetationReading,
    WeatherMetrics,
    FireDetection,
    GroundReport,
    CauseCategory,
    WorkOrderStatus,
)
from vanasetu.agents.coordinator import VanaSetuCoordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eval_harness")


class EvaluationHarness:
    """
    Evaluates VanaSetu agents against benchmark historical datasets.
    """

    def __init__(self, test_cases_path: Optional[str] = None):
        if test_cases_path:
            self.path = Path(test_cases_path)
        else:
            self.path = Path(__file__).parent / "test_cases.json"
        self.coordinator = VanaSetuCoordinator()

    def load_test_cases(self) -> List[Dict[str, Any]]:
        """Loads benchmark scenarios from JSON."""
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_benchmark(self) -> Dict[str, Any]:
        """
        Executes all test cases and calculates performance metrics.
        """
        cases = self.load_test_cases()
        total = len(cases)
        correct_diagnoses = 0
        policy_adherence_count = 0
        false_alarms_suppressed = 0
        dfo_escalation_matches = 0

        results = []
        start_all = time.time()

        for tc in cases:
            case_id = tc["case_id"]
            parcel_id = tc["parcel_id"]
            expected_cause = CauseCategory(tc["expected_cause"])
            expected_valid = tc["expected_verification_valid"]
            expected_dfo = tc.get("expected_dfo_approval", False)

            # Reconstruct model objects with scenario dates
            telemetry_data = tc.get("telemetry")
            telemetry = None
            if telemetry_data:
                telemetry_dict = dict(telemetry_data)
                if "timestamp" not in telemetry_dict:
                    telemetry_dict["timestamp"] = tc.get("timestamp", "2024-08-01T10:30:00Z")
                telemetry = VegetationReading(parcel_id=parcel_id, **telemetry_dict)

            weather_data = tc.get("weather")
            weather = None
            if weather_data:
                weather_dict = dict(weather_data)
                if "observation_date" not in weather_dict:
                    weather_dict["observation_date"] = tc.get("observation_date", "2024-08-01")
                weather = WeatherMetrics(parcel_id=parcel_id, **weather_dict)

            fires = [FireDetection(**f) for f in tc.get("fires", [])]
            ground = GroundReport(**tc["ground_report"]) if tc.get("ground_report") else None

            t0 = time.time()
            output = self.coordinator.process_parcel_alert(
                parcel_id=parcel_id,
                custom_telemetry=telemetry,
                custom_weather=weather,
                custom_fires=fires,
                custom_ground=ground,
            )
            elapsed = time.time() - t0

            diagnosis = output["diagnosis"]
            verification = output["verification"]
            work_order = output["work_order"]

            # Effective cause is after verification override (if any)
            actual_cause = verification.overridden_cause or (diagnosis.primary_cause if diagnosis else CauseCategory.UNKNOWN)
            is_valid = verification.is_valid if verification else False
            dfo_actual = work_order.dfo_approval_required if work_order else False

            # Checks
            match_diag = (actual_cause == expected_cause)
            match_valid = (is_valid == expected_valid)
            match_dfo = (dfo_actual == expected_dfo)

            if match_diag:
                correct_diagnoses += 1
            if match_valid:
                policy_adherence_count += 1
            if match_dfo:
                dfo_escalation_matches += 1

            # Check false alarm suppression
            if expected_cause in [CauseCategory.SENSOR_ARTIFACT_FALSE_ALARM, CauseCategory.PHENOLOGICAL_SHEDDING]:
                if actual_cause == expected_cause:
                    false_alarms_suppressed += 1

            results.append({
                "case_id": case_id,
                "name": tc["name"],
                "parcel_id": parcel_id,
                "expected_cause": expected_cause.value,
                "actual_cause": actual_cause.value,
                "diagnosis_match": match_diag,
                "expected_valid": expected_valid,
                "actual_valid": is_valid,
                "policy_match": match_valid,
                "expected_dfo": expected_dfo,
                "actual_dfo": dfo_actual,
                "latency_sec": round(elapsed, 4),
                "work_order_id": work_order.work_order_id if work_order else None,
                "cost_inr": work_order.estimated_cost_inr if work_order else 0.0,
            })

        total_elapsed = time.time() - start_all
        accuracy = round((correct_diagnoses / total) * 100.0, 2)
        policy_rate = round((policy_adherence_count / total) * 100.0, 2)
        dfo_rate = round((dfo_escalation_matches / total) * 100.0, 2)

        summary = {
            "total_benchmark_cases": total,
            "diagnostic_accuracy_pct": accuracy,
            "policy_adherence_pct": policy_rate,
            "dfo_escalation_accuracy_pct": dfo_rate,
            "false_alarms_suppressed": false_alarms_suppressed,
            "total_evaluation_time_sec": round(total_elapsed, 3),
            "average_latency_per_case_sec": round(total_elapsed / total, 4),
            "results": results,
        }

        # Save report
        out_dir = Path(__file__).parent
        with open(out_dir / "eval_report.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Generate markdown report
        self._write_markdown_report(summary, out_dir / "eval_report.md")

        return summary

    def _write_markdown_report(self, summary: Dict[str, Any], filepath: Path) -> None:
        """Writes a clean, formatted GitHub-style markdown report."""
        lines = [
            "# VanaSetu Historical Benchmark Evaluation Report",
            f"**Execution Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary Metrics",
            f"- **Total Test Cases**: {summary['total_benchmark_cases']}",
            f"- **Diagnostic Causal Accuracy**: `{summary['diagnostic_accuracy_pct']}%`",
            f"- **Deterministic Policy Adherence**: `{summary['policy_adherence_pct']}%`",
            f"- **DFO Escalation Threshold Precision**: `{summary['dfo_escalation_accuracy_pct']}%`",
            f"- **False Alarms Successfully Suppressed**: `{summary['false_alarms_suppressed']}`",
            f"- **Total Elapsed Time**: `{summary['total_evaluation_time_sec']}s` (avg `{summary['average_latency_per_case_sec']}s/case`)",
            "",
            "## Case-by-Case Breakdown",
            "| Case ID | Scenario Name | Expected Cause | Actual Diagnosed | Diag Match | Policy Valid | DFO Req | Cost (INR) |",
            "|---|---|---|---|:---:|:---:|:---:|---:|",
        ]

        for r in summary["results"]:
            diag_icon = "✅" if r["diagnosis_match"] else "❌"
            valid_icon = "✅" if r["policy_match"] else "❌"
            lines.append(
                f"| `{r['case_id']}` | {r['name']} | `{r['expected_cause']}` | `{r['actual_cause']}` | {diag_icon} | {valid_icon} | {r['actual_dfo']} | ₹{r['cost_inr']:,.0f} |"
            )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def main():
    harness = EvaluationHarness()
    summary = harness.run_benchmark()
    print("=" * 70)
    print("VanaSetu Historical Evaluation Benchmark Complete")
    print(f"Accuracy: {summary['diagnostic_accuracy_pct']}% | Policy Adherence: {summary['policy_adherence_pct']}%")
    print(f"Avg Latency: {summary['average_latency_per_case_sec']}s/case")
    print("=" * 70)


if __name__ == "__main__":
    main()
