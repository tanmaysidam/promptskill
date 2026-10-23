# VanaSetu Historical Benchmark Evaluation Report
**Execution Date**: 2026-10-23 13:52:32

## Summary Metrics
- **Total Test Cases**: 6
- **Diagnostic Causal Accuracy**: `100.0%`
- **Deterministic Policy Adherence**: `100.0%`
- **DFO Escalation Threshold Precision**: `100.0%`
- **False Alarms Successfully Suppressed**: `2`
- **Total Elapsed Time**: `0.009s` (avg `0.0015s/case`)

## Case-by-Case Breakdown
| Case ID | Scenario Name | Expected Cause | Actual Diagnosed | Diag Match | Policy Valid | DFO Req | Cost (INR) |
|---|---|---|---|:---:|:---:|:---:|---:|
| `TC-001-VIDARBHA-DROUGHT` | Vidarbha Post-Monsoon Severe Drought Stress | `DROUGHT_STRESS` | `DROUGHT_STRESS` | ✅ | ✅ | True | ₹48,750 |
| `TC-002-SIMILIPAL-FIRE` | Similipal Buffer Active Wildfire Encroachment | `SURFACE_FIRE_SCORCH` | `SURFACE_FIRE_SCORCH` | ✅ | ✅ | True | ₹72,000 |
| `TC-003-WESTERNGHATS-LANTANA` | Western Ghats Invasive Lantana Weed Smothering | `INVASIVE_WEED_CHOKING` | `INVASIVE_WEED_CHOKING` | ✅ | ✅ | True | ₹36,000 |
| `TC-004-ADILABAD-GRAZING` | Adilabad Solar Fence Breach and Cattle Trampling | `GRAZING_DAMAGE` | `GRAZING_DAMAGE` | ✅ | ✅ | True | ₹35,000 |
| `TC-005-KONKAN-CLOUD-ARTIFACT` | Konkan Coastal Monsoon Cloud Shadow False Alarm | `SENSOR_ARTIFACT_FALSE_ALARM` | `SENSOR_ARTIFACT_FALSE_ALARM` | ✅ | ✅ | False | ₹0 |
| `TC-006-BANDHAVGARH-PHENOLOGY` | Bandhavgarh Teak Seasonal Deciduous Leaf-Fall | `PHENOLOGICAL_SHEDDING` | `PHENOLOGICAL_SHEDDING` | ✅ | ✅ | False | ₹0 |