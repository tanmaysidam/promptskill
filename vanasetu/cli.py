"""
VanaSetu Command Line Interface (CLI)
=====================================
Interactive CLI for managing plantation monitoring, triggering ingestion pipelines,
evaluating at-risk parcels with ADK agents, and inspecting work orders.
"""

from __future__ import annotations

import sys
import json
import argparse
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from vanasetu.tools.bigquery_tool import BigQueryTool
from vanasetu.pipeline.pipeline_runner import PipelineRunner
from vanasetu.agents.coordinator import VanaSetuCoordinator
from vanasetu.evals.eval_harness import EvaluationHarness


def print_banner():
    banner = r"""
  __      __                 ____       _         
  \ \    / /                / ___|  ___| |_ _   _ 
   \ \  / /_ _ _ __   __ _  \___ \ / _ \ __| | | |
    \ \/ / _` | '_ \ / _` |  ___) |  __/ |_| |_| |
     \__/ \__,_|_| |_|\__,_| |____/ \___|\__|\__,_|
      Early-Warning Forest Restoration Monitoring
    """
    print(banner)


def cmd_list_parcels(args):
    """Lists all monitored forest parcels."""
    bq = BigQueryTool()
    parcels = bq.list_parcels()
    print(f"\nMonitored Plantation Parcels ({len(parcels)} total):")
    print("-" * 95)
    print(f"{'Parcel ID':<18} {'State':<14} {'Division':<25} {'Area (ha)':<10} {'Species Count':<14} {'Officer':<18}")
    print("-" * 95)
    for p in parcels:
        species_sum = sum(s.count for s in p.species_mix)
        print(f"{p.parcel_id:<18} {p.state:<14} {p.forest_division[:24]:<25} {p.area_hectares:<10.1f} {species_sum:<14} {p.assigned_officer.split()[0]:<18}")
    print("-" * 95)


def cmd_run_pipeline(args):
    """Executes ingestion jobs and anomaly detection."""
    print("\nExecuting VanaSetu Daily Ingestion Pipeline...")
    runner = PipelineRunner()
    res = runner.run_daily_monitoring()
    print(f"Total Parcels Monitored: {res['total_parcels_monitored']}")
    print(f"Normal Parcels:          {res['normal_count']}")
    print(f"At-Risk Anomaly Parcels: {res['anomalous_count']}")

    if res["anomalous_count"] > 0:
        print("\n[!] Parcels Queued for Multi-Agent Triage:")
        for item in res["at_risk_queue"]:
            p = item["parcel"]
            t = item["telemetry"]
            print(f" - {p.parcel_id} ({p.state}, {p.district}): NDVI drop {t.ndvi_drop_pct}% (Z-Score: {t.z_score})")
    else:
        print("\nAll parcels within baseline variance.")


def cmd_triage_parcel(args):
    """Executes full multi-agent triage, diagnosis, and policy verification on a parcel."""
    parcel_id = args.parcel_id
    print(f"\nInitiating Multi-Agent Early Warning Assessment for Parcel: {parcel_id}")
    coordinator = VanaSetuCoordinator()

    try:
        output = coordinator.process_parcel_alert(parcel_id)
    except ValueError as e:
        print(f"Error: {e}")
        return

    parcel = output["parcel"]
    telemetry = output["telemetry"]
    weather = output["weather"]
    fires = output["fires"]
    triage = output["triage"]
    diagnosis = output["diagnosis"]
    verification = output["verification"]
    work_order = output["work_order"]

    print("\n" + "=" * 80)
    print(f"PARCEL: {parcel.parcel_id} | {parcel.forest_division}, {parcel.state}")
    print(f"Area: {parcel.area_hectares} ha | Soil: {parcel.soil_type} | Scheme: {parcel.afforestation_scheme}")
    print("=" * 80)

    print("\n[1] SENTINEL TRIAGE AGENT:")
    print(f"  • Urgency Level:      {triage.get('urgency', 'N/A')}")
    print(f"  • Escalate:           {triage.get('escalate_to_diagnosis', False)}")
    print(f"  • Cloud Cover:        {telemetry.cloud_cover_pct if telemetry else 0.0}%")
    print(f"  • Triage Assessment:  {triage.get('triage_summary')}")

    if diagnosis:
        print("\n[2] DIAGNOSTIC REASONING AGENT:")
        print(f"  • Primary Cause:      {diagnosis.primary_cause.value}")
        print(f"  • Confidence:         {diagnosis.confidence_score * 100:.1f}%")
        print(f"  • Diagnosis Summary:  {diagnosis.reasoning_summary}")
        if diagnosis.supporting_evidence:
            print("  • Supporting Evidence:")
            for ev in diagnosis.supporting_evidence:
                print(f"     - {ev}")

    if verification:
        print("\n[3] DETERMINISTIC POLICY VERIFIER:")
        print(f"  • Policy Status:      {'APPROVED / VALID' if verification.is_valid else 'VIOLATION DETECTED'}")
        if verification.overridden_cause:
            print(f"  • Overridden Cause:   {verification.overridden_cause.value}")
        print(f"  • DFO Approval Req:   {verification.dfo_approval_required}")
        print("  • Rule Verifications:")
        for line in verification.explanation.splitlines():
            print(f"     {line}")

    if work_order:
        print("\n[4] FIELD ACTION WORK ORDER:")
        print(f"  • Work Order ID:      {work_order.work_order_id}")
        print(f"  • Status:             {work_order.status.value}")
        print(f"  • Urgency:            {work_order.urgency.value}")
        print(f"  • Assigned Crew:      {work_order.assigned_beat_guard} ({work_order.contact_phone})")
        print(f"  • Estimated Cost:     INR ₹{work_order.estimated_cost_inr:,.2f}")
        print(f"  • DFO Approval Gate:  {'REQUIRED (Cost > ₹15,000)' if work_order.dfo_approval_required else 'Not Required'}")
        print(f"\n  • English Instructions:\n    {work_order.crew_instructions_en}")
        print(f"\n  • Hindi Instructions (हिंदी निर्देश):\n    {work_order.crew_instructions_hi}")
        print(f"\n  • Equipment:          {', '.join(work_order.required_equipment)}")
    print("=" * 80)


def cmd_list_work_orders(args):
    """Lists all generated work orders."""
    bq = BigQueryTool()
    orders = bq.list_work_orders(parcel_id=args.parcel_id)
    print(f"\nPersisted Work Orders ({len(orders)} total):")
    print("-" * 100)
    print(f"{'Order ID':<22} {'Parcel ID':<18} {'Urgency':<10} {'Diagnosed Cause':<26} {'Cost (INR)':<12} {'DFO Gate':<8}")
    print("-" * 100)
    for o in orders:
        print(f"{o.work_order_id:<22} {o.parcel_id:<18} {o.urgency.value:<10} {o.diagnosed_cause.value[:25]:<26} ₹{o.estimated_cost_inr:<10,.0f} {'YES' if o.dfo_approval_required else 'NO':<8}")
    print("-" * 100)


def cmd_run_evals(args):
    """Executes historical benchmark evaluation."""
    print("\nRunning VanaSetu Benchmark Evaluation Harness...")
    harness = EvaluationHarness()
    summary = harness.run_benchmark()
    print("\n" + "=" * 70)
    print(f"BENCHMARK RESULTS: {summary['total_benchmark_cases']} Scenarios Evaluated")
    print("=" * 70)
    print(f"Diagnostic Accuracy:         {summary['diagnostic_accuracy_pct']}%")
    print(f"Policy Adherence Rate:       {summary['policy_adherence_pct']}%")
    print(f"DFO Threshold Accuracy:      {summary['dfo_escalation_accuracy_pct']}%")
    print(f"False Alarms Suppressed:     {summary['false_alarms_suppressed']}")
    print(f"Total Latency:               {summary['total_evaluation_time_sec']}s (avg {summary['average_latency_per_case_sec']}s/case)")
    print("=" * 70)
    print("Detailed report written to: vanasetu/evals/eval_report.md")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="VanaSetu - Forest Restoration Multi-Agent Early-Warning System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: list-parcels
    subparsers.add_parser("list-parcels", help="List monitored plantation parcels")

    # Command: run-pipeline
    subparsers.add_parser("run-pipeline", help="Run ingestion pipeline and anomaly detection")

    # Command: triage-parcel
    triage_parser = subparsers.add_parser("triage-parcel", help="Run multi-agent triage and diagnosis on a parcel")
    triage_parser.add_argument("parcel_id", type=str, help="Parcel ID (e.g. MH-YTL-2024-001)")

    # Command: list-work-orders
    wo_parser = subparsers.add_parser("list-work-orders", help="List persisted field work orders")
    wo_parser.add_argument("--parcel-id", type=str, default=None, help="Filter by parcel ID")

    # Command: run-evals
    subparsers.add_parser("run-evals", help="Execute evaluation benchmark harness")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "list-parcels": cmd_list_parcels,
        "run-pipeline": cmd_run_pipeline,
        "triage-parcel": cmd_triage_parcel,
        "list-work-orders": cmd_list_work_orders,
        "run-evals": cmd_run_evals,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()
