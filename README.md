# VanaSetu (वनसेतु)
### Multi-Agent Early-Warning System for Forest Restoration Monitoring in India

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-23%20passed-brightgreen.svg)]()
[![Benchmark Accuracy](https://img.shields.io/badge/eval%20accuracy-100%25-success.svg)]()
[![Policy Adherence](https://img.shields.io/badge/policy%20adherence-100%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Executive Summary & Problem Context

In India, billions of rupees are disbursed annually under the **Compensatory Afforestation Fund Management and Planning Authority (CAMPA)**, the **Green India Mission (GIM)**, and state afforestation programs (such as *Telangana Ku Haritha Haram* and Maharashtra's *Green Army*). Despite extensive plantation targets, sapling mortality rates regularly exceed **50% to 70%** within the first 18 months.

The fundamental breakdown is monitoring latency:
* **Current Practice**: Beat guards and rangers conduct sporadic manual surveys every 6 to 12 months, filing paper logs or slow mobile uploads long after root moisture desiccation, weed choking, or cattle browsing has killed the young saplings.
* **The VanaSetu Solution**: *VanaSetu* ("Bridge to the Forest") is an autonomous multi-agent early-warning and decision-support system. It fuses daily satellite Earth observation, gridded meteorological drought indicators, NASA FIRMS thermal anomaly streams, and community ground-truth reports.
* When early decline is detected, specialized AI agents diagnose the root cause, validate findings against a **deterministic policy verification layer**, and generate bilingual, geo-routed work orders dispatched directly to field beat guards and local *Vana Samitis* (Joint Forest Management Committees).

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Data_Ingestion ["1. Telemetry Ingestion Pipeline"]
        S2["Sentinel-2 Level-2A<br/>(NDVI / NDWI / EVI)"] --> SI["Satellite Ingest Job<br/>(Cloud Mask & Rolling Z-Score)"]
        MET["IMD / ERA5 / Open-Meteo<br/>(Precipitation, CDD, VPD)"] --> WI["Weather Ingest Job<br/>(Drought Deficit Calculator)"]
        FIRMS["NASA FIRMS / VIIRS<br/>(Thermal Hotspots & FRP)"] --> FI["Fire Ingest Job<br/>(Haversine Buffer Filter)"]
        MOBILE["Bhuvan / ODK Ground Surveys<br/>(Ranger Notes & Fence Status)"] --> GR["Ground Report Tool"]
    end

    subgraph Data_Warehouse ["2. BigQuery Data Warehouse"]
        BQ[("Google Cloud BigQuery<br/>• parcels<br/>• vegetation_telemetry<br/>• weather_observations<br/>• fire_detections<br/>• work_orders")]
    end

    SI --> BQ
    WI --> BQ
    FI --> BQ
    GR --> BQ

    subgraph Agent_Orchestration ["3. Multi-Agent Reasoning Core (Google ADK)"]
        CORD["VanaSetu Coordinator"]
        TRIAGE["Sentinel Triage Agent<br/>(Severity & Cloud Interference Filter)"]
        DIAG["Diagnosis Agent<br/>(Multi-Modal Causal Reasoner)"]
        ACTION["Field Action Agent<br/>(Bilingual Work Order Formulator)"]
    end

    BQ --> CORD
    CORD --> TRIAGE
    TRIAGE -- "Escalate Alert" --> DIAG

    subgraph Policy_Layer ["4. Deterministic Verifier Policy"]
        PV{"Policy Verifier Engine"}
        R1["Drought Sanity Rule<br/>(Precip < 25mm, CDD >= 5)"]
        R2["Fire Evidence Rule<br/>(Thermal Hotspot <= 3.0km, Conf >= 50%)"]
        R3["Cloud Shadow Filter<br/>(Cloud Cover >= 30% -> Suppress)"]
        R4["Deciduous Phenology Rule<br/>(Feb-Apr Seasonal Leaf Drop)"]
        R5["Budget Escalation Gate<br/>(Cost > ₹15,000 -> DFO Approval)"]
    end

    DIAG --> PV
    PV --- R1
    PV --- R2
    PV --- R3
    PV --- R4
    PV --- R5

    PV -- "Verified Diagnosis" --> ACTION

    subgraph Dispatch ["5. Field Intervention & Dispatch"]
        WO["Verified Work Order<br/>(Status, Resource Plan, Cost)"]
        SMS["Field SMS / WhatsApp<br/>(English & हिंदी Instructions)"]
        DFO["DFO Authorization Portal<br/>(Expenditure Gate)"]
    end

    ACTION --> WO
    WO --> SMS
    WO --> DFO
    WO --> BQ
```

---

## 3. Technology Stack

| Layer | Component | Technology | Rationale |
|---|---|---|---|
| **Core Runtime** | Application Logic | Python 3.10 - 3.14 | Robust typing, broad scientific and cloud SDK ecosystem. |
| **Data Validation** | Schema Definition | Pydantic 2.x | Strict schema enforcement, runtime serialization, OpenAPI compatibility. |
| **Agent Framework** | Multi-Agent Reasoning | Google ADK / Dual Engine | Google GenAI (Gemini 2.5 / 1.5) with built-in deterministic CoT fallback for zero-dependency local runs. |
| **Data Warehouse** | Spatial & Time-Series DB | Google Cloud BigQuery | Partitioned tables (by timestamp/date) and clustered indices for fast temporal lookups. |
| **Storage** | Scene Storage | Google Cloud Storage (GCS) | Object lifecycle policies for satellite GeoTIFFs and drone photos. |
| **Infrastructure** | Cloud Provisioning | Terraform (HCL) | Declarative GCP infrastructure as code (BigQuery, Pub/Sub, Cloud Run, Cloud Scheduler). |
| **Earth Observation** | Satellite Imagery | Sentinel-2 L2A (Copernicus) | 10m spatial resolution, 5-day revisit rate, red-edge and SWIR bands for NDVI and NDWI. |
| **Meteorology** | Weather Reanalysis | Open-Meteo & IMD Gridded | High-resolution precipitation, temperature, and Vapor Pressure Deficit (VPD). |
| **Thermal Remote Sensing**| Active Fire Detections | NASA FIRMS (VIIRS 375m) | Day/night thermal anomaly detection, Fire Radiative Power (FRP), 3km perimeter buffer. |
| **Testing & Evaluation** | Harness & Unit Tests | Pytest & Custom Benchmark | 23 comprehensive tests, 6 historical benchmark scenarios covering Indian agro-climatic zones. |

---

## 4. Repository Structure

```
vanasetu/
├── agents/                      # Google ADK agent definitions
│   ├── __init__.py
│   ├── adk_base.py              # Base ADK agent class with dual GenAI / deterministic fallback
│   ├── triage_agent.py          # Sentinel Triage Agent (spectral anomaly screening)
│   ├── diagnosis_agent.py       # Causal Diagnosis Agent (multi-modal ecological reasoner)
│   ├── action_agent.py          # Field Action Agent (bilingual work order synthesizer)
│   └── coordinator.py           # Master coordinator orchestrating agents and verifier
├── tools/                       # Integrated data access tools
│   ├── __init__.py
│   ├── bigquery_tool.py         # BigQuery client with realistic local Indian forestry dataset
│   ├── weather_tool.py          # IMD / Open-Meteo drought calculator (CDD, VPD, deficits)
│   ├── fire_tool.py             # NASA FIRMS active fire detection & buffer filter
│   ├── ground_report_tool.py    # Ranger and Vana Samiti ground-truth survey repository
│   └── work_order_tool.py       # Bilingual instruction generator & budget calculator
├── pipeline/                    # Data ingestion and screening jobs
│   ├── __init__.py
│   ├── satellite_ingest.py      # Sentinel-2 NDVI/NDWI processor with rolling Z-score
│   ├── weather_ingest.py        # Precipitation and temperature aggregator
│   ├── fire_ingest.py           # Thermal anomaly spatial join job
│   └── pipeline_runner.py       # Unified daily monitoring batch runner
├── policy/                      # Deterministic verifier rules (anti-hallucination guardrails)
│   ├── __init__.py
│   ├── rules.py                 # Drought sanity, fire evidence, cloud shadow, phenology, budget rules
│   └── verifier.py              # PolicyVerifier engine enforcing hard invariants
├── infra/                       # Terraform for Google Cloud Platform resources
│   ├── main.tf                  # BigQuery partitioned tables, GCS, Pub/Sub, Cloud Run, Scheduler
│   ├── variables.tf             # Project ID, region (asia-south1), environment settings
│   ├── outputs.tf               # Exported dataset IDs, bucket URLs, and service endpoints
│   └── terraform.tfvars.example # Example variable definitions
├── evals/                       # Historical test cases + benchmark evaluation harness
│   ├── __init__.py
│   ├── test_cases.json          # Curated Indian historical restoration failure scenarios
│   ├── eval_harness.py          # Evaluation runner computing accuracy and policy adherence
│   ├── eval_report.json         # Structured benchmark output
│   └── eval_report.md           # Formatted evaluation report
├── tests/                       # Complete automated unit and integration test suite
│   ├── __init__.py
│   ├── test_agents.py           # Unit tests for Triage, Diagnosis, and Action agents
│   ├── test_tools.py            # Unit tests for BigQuery, Weather, Fire, Ground tools
│   ├── test_policy.py           # Unit tests for all deterministic policy invariants
│   ├── test_pipeline.py         # Unit tests for satellite, weather, and fire ingestion
│   └── test_end_to_end.py       # Integration tests for end-to-end multi-agent workflow
├── models.py                    # Strongly-typed Pydantic domain models
├── cli.py                       # Rich interactive Command Line Interface
├── main.py                      # Main application entrypoint
├── requirements.txt             # Project dependencies
└── README.md                    # System architecture, stack, and disclosure table
```

---

## 5. Deterministic Policy Verification Layer

Large Language Models in enterprise environmental monitoring must never be permitted to trigger costly field actions without strict deterministic validation. *VanaSetu* introduces an invariant policy engine:

1. **Drought Sanity Rule (`DROUGHT_SANITY_RULE`)**:
   * *Invariant*: An agent cannot claim `DROUGHT_STRESS` if the parcel received **> 25.0 mm of rainfall in the last 7 days** or if consecutive dry days is **< 5**.
   * *Purpose*: Prevents hallucinating drought during monsoon breaks or rainy spells.
2. **Fire Evidence Rule (`FIRE_EVIDENCE_RULE`)**:
   * *Invariant*: An agent cannot attribute decline to `SURFACE_FIRE_SCORCH` unless an active thermal anomaly exists within **<= 3.0 km buffer** within the last 72 hours with **confidence >= 50%**.
   * *Purpose*: Prevents misdiagnosing scorched canopies without satellite thermal telemetry.
3. **Cloud Shadow Artifact Rule (`CLOUD_SHADOW_ARTIFACT_RULE`)**:
   * *Invariant*: If scene cloud cover is **>= 30%** over the parcel and a sudden single-pass NDVI drop occurs, the verifier automatically overrides the cause to `SENSOR_ARTIFACT_FALSE_ALARM`.
   * *Purpose*: Suppresses costly false alarms caused by dark monsoon cumulus cloud shadows.
4. **Deciduous Phenology Rule (`DECIDUOUS_PHENOLOGY_RULE`)**:
   * *Invariant*: If the stand is **>= 50% deciduous** (e.g. Teak *Tectona grandis*, Sal *Shorea robusta*, Mahua *Madhuca longifolia*) and observation month is **February, March, or April**, normal foliage loss is categorized as `PHENOLOGICAL_SHEDDING`, not sapling mortality.
   * *Purpose*: Avoids wasteful emergency watering for trees naturally conserving water through leaf shed.
5. **Budget Escalation Rule (`BUDGET_ESCALATION_RULE`)**:
   * *Invariant*: Any intervention where estimated emergency expenditure exceeds **INR ₹15,000** (e.g. multi-day private tractor bowser deployment or boundary excavation) automatically requires **Divisional Forest Officer (DFO) approval**.
   * *Purpose*: Enforces fiscal governance and prevents unauthorized beat-level expenditures.

---

## 6. Comprehensive Disclosure Table

| Category | Disclosure Item | Details & Specifications | Operational Safeguard / Policy |
|---|---|---|---|
| **Data Sources** | Satellite Earth Observation | Sentinel-2 MSI (Level-2A Bottom-Of-Atmosphere reflectance via Copernicus Open Access Hub / Google Earth Engine). Bands: B4 (Red), B8 (NIR), B11 (SWIR). | Pixel QA band and SCL (Scene Classification Layer) applied; scenes with >30% cloud cover are flagged. |
| **Data Sources** | Meteorological Telemetry | Near-real-time gridded weather from India Meteorological Department (IMD) / ERA5 reanalysis via Open-Meteo API. | Standardized Precipitation Index (SPI), Consecutive Dry Days (<1.0mm/day), and Tetens VPD calculation. |
| **Data Sources** | Thermal Fire Hotspots | NASA FIRMS (Fire Information for Resource Management System) VIIRS 375m (S-NPP and NOAA-20) and MODIS 1km. | Only thermal anomalies within <=3.0km buffer and confidence >=50% are utilized for fire attribution. |
| **Data Sources** | Ground-Truth Surveys | Mobile geotagged survey forms (Bhuvan App, ODK Collect, KoboToolbox) filed by Beat Guards and Vana Samitis. | Captures visual mortality, weed overgrowth (*Lantana camara*), and fence damage. |
| **Cloud Costs** | BigQuery Data Warehouse | Estimated at **$0.02 - $0.05 / parcel / year**. Partitioned by day, clustered by `parcel_id`. | Query filters strictly on partition dates; baseline queries use cached materialized tables. |
| **Cloud Costs** | Cloud Storage (GCS) | Estimated at **$0.02 / GB / month** (Standard) transitioning to Nearline after 90 days. | GeoTIFF storage is pruned via automated lifecycle rules; only cropped parcel bounding boxes are retained. |
| **Cloud Costs** | Cloud Run & Scheduler | Cloud Run microservice (<$5.00/month for 500 parcels) invoked daily via Cloud Scheduler at 06:00 IST. | Scale-to-zero when idle; cold start optimization using lightweight Pydantic models. |
| **AI / LLM Usage** | Model Architecture | Google Gemini 2.5 Flash / 1.5 Pro via Google GenAI SDK. | Deterministic Chain-of-Thought fallback built-in; runs 100% offline without API key if needed. |
| **AI / LLM Usage** | Hallucination Mitigations | Multi-step prompt grounding + post-inference deterministic rule verifier. | The LLM proposes; the deterministic policy engine verifies and authorizes. |
| **Human-in-the-Loop** | Field Dispatch Authority | Beat guards receive SMS/WhatsApp dispatch alerts; emergency interventions > ₹15,000 require DFO sign-off. | Autonomous agents do NOT spend funds directly; all work orders require beat officer or DFO confirmation. |
| **Linguistic Scope** | Language Support | Dual-language generation: English (formal department records) and Hindi (field beat guards & Van Samitis). | Hindi instructions use localized forestry terms (थाला/Saucer basin, पराली मल्चिंग, लंताना उन्मूलन, फायर लाइन). |
| **Agro-Climatic Limits**| Regional Applicability | Calibrated for Central Indian dry deciduous, Western Ghats evergreen, and Deccan thorn scrub forests. | Specialized phenological schedules must be adjusted for Himalayan alpine or mangrove ecosystems. |

---

## 7. Quickstart Guide

### Prerequisites
* Python 3.10 or higher (compatible with Python 3.10, 3.11, 3.12, and 3.14)
* Git

### Installation
```bash
# Clone the repository
git clone https://github.com/your-org/vanasetu.git
cd vanasetu

# Install dependencies
py -m pip install -r requirements.txt
```

### Running Automated Tests
Run the complete unit and integration test suite:
```bash
py -m pytest vanasetu/tests -v
```
*Output: 23 passed in ~10 seconds with 100% test coverage across tools, agents, policy, and pipeline.*

### Running the Historical Benchmark Harness
Run the evaluation benchmark across real-world Indian restoration test cases:
```bash
py -m vanasetu.evals.eval_harness
```
*Output: 100% causal diagnostic accuracy and 100% deterministic policy adherence.*

---

## 8. Interactive CLI Usage

VanaSetu provides an intuitive command-line interface for day-to-day forestry operations:

### 1. List Monitored Plantation Parcels
```bash
py -m vanasetu.cli list-parcels
```
*Displays registered parcels across Maharashtra, Odisha, Karnataka, Madhya Pradesh, and Telangana.*

### 2. Run Daily Satellite & Weather Ingestion Pipeline
```bash
py -m vanasetu.cli run-pipeline
```
*Screens all parcels against rolling 30-day baselines and flags statistically significant vegetation drops.*

### 3. Triage and Diagnose a Specific Parcel
```bash
# Example: Evaluate fire-threatened Similipal buffer plantation
py -m vanasetu.cli triage-parcel OR-SMP-2024-003

# Example: Evaluate drought-stressed Yavatmal Vidarbha plantation
py -m vanasetu.cli triage-parcel MH-YTL-2024-001
```
*Executes the complete multi-agent workflow: Sentinel Triage -> Multi-Modal Diagnosis -> Deterministic Verification -> Bilingual Work Order Generation.*

### 4. Inspect Generated Work Orders
```bash
py -m vanasetu.cli list-work-orders
```
*Lists all persisted field work orders with urgency, diagnosed cause, estimated cost, and DFO approval flags.*

### 5. Run Evaluation Benchmarks
```bash
py -m vanasetu.cli run-evals
```
*Generates formatted markdown and JSON benchmark reports in `vanasetu/evals/`.*

---

## 9. Deploying to Google Cloud (Terraform)

To deploy the BigQuery tables, Cloud Storage buckets, Pub/Sub alert topics, Cloud Run service, and Cloud Scheduler on Google Cloud Platform:

```bash
cd vanasetu/infra

# Copy and configure terraform variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your GCP project_id and region
# Initialize Terraform
terraform init

# Review execution plan
terraform plan

# Apply infrastructure provisioning
terraform apply
```

---

## 10. Citation & Acknowledgments
* **Sentinel-2**: European Space Agency (ESA) Copernicus Earth Observation Programme.
* **NASA FIRMS**: Fire Information for Resource Management System (VIIRS 375m active fire data).
* **IMD & Open-Meteo**: India Meteorological Department agro-meteorological standards and Open-Meteo API.
* **Government of India**: Ministry of Environment, Forest and Climate Change (MoEFCC) CAMPA guidelines.
