-- =============================================================================
-- VanaSetu BigQuery Schema
-- Datasets: core, ops, audit
-- Region: asia-south1
-- All time-series tables partitioned by date, clustered by site_id,
-- and configured with require_partition_filter = true.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DATASET: core
-- Contains site baselines, satellite indices, weather, and fire telemetry
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `core.sites` (
  site_id STRING NOT NULL OPTIONS(description="Unique plantation site identifier (e.g. MH-YTL-2024-001)"),
  state STRING NOT NULL,
  district STRING NOT NULL,
  forest_division STRING NOT NULL,
  range_name STRING NOT NULL,
  beat_name STRING NOT NULL,
  latitude FLOAT64 NOT NULL,
  longitude FLOAT64 NOT NULL,
  area_hectares FLOAT64 NOT NULL,
  plantation_date DATE NOT NULL,
  afforestation_scheme STRING,
  species_mix ARRAY<STRUCT<
    species_name STRING,
    common_name STRING,
    count INT64,
    is_deciduous BOOL,
    drought_tolerance STRING
  >>,
  soil_type STRING,
  irrigation_type STRING,
  fencing_type STRING,
  assigned_officer STRING,
  officer_phone STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS `core.satellite_telemetry` (
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  ndvi FLOAT64 NOT NULL,
  ndwi FLOAT64 NOT NULL,
  evi FLOAT64,
  cloud_cover_pct FLOAT64 NOT NULL,
  baseline_ndvi_mean FLOAT64 NOT NULL,
  baseline_ndvi_std FLOAT64 NOT NULL,
  ndvi_drop_pct FLOAT64 NOT NULL,
  z_score FLOAT64 NOT NULL,
  is_anomaly BOOL NOT NULL
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "Sentinel-2 and Landsat surface reflectance indices"
);

CREATE TABLE IF NOT EXISTS `core.weather_observations` (
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  precipitation_mm_7d FLOAT64 NOT NULL,
  precipitation_mm_14d FLOAT64 NOT NULL,
  precipitation_mm_30d FLOAT64 NOT NULL,
  rainfall_deficit_pct FLOAT64 NOT NULL,
  max_temperature_c FLOAT64 NOT NULL,
  consecutive_dry_days INT64 NOT NULL,
  vapor_pressure_deficit_kpa FLOAT64 NOT NULL,
  heatwave_alert BOOL NOT NULL,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "IMD gridded and ERA5 reanalysis weather metrics"
);

CREATE TABLE IF NOT EXISTS `core.fire_events` (
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  fire_id STRING NOT NULL,
  detected_at TIMESTAMP NOT NULL,
  satellite_sensor STRING NOT NULL,
  confidence_pct FLOAT64 NOT NULL,
  brightness_temp_k FLOAT64 NOT NULL,
  frp_mw FLOAT64 NOT NULL,
  distance_km FLOAT64 NOT NULL,
  within_buffer BOOL NOT NULL
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "NASA FIRMS VIIRS and MODIS active thermal anomalies"
);

-- -----------------------------------------------------------------------------
-- DATASET: ops
-- Operational actions: diagnostic interventions and field work orders
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `ops.interventions` (
  intervention_id STRING NOT NULL,
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  created_at TIMESTAMP NOT NULL,
  primary_cause STRING NOT NULL,
  confidence_score FLOAT64 NOT NULL,
  urgency STRING NOT NULL,
  reasoning_summary STRING NOT NULL,
  proposed_actions ARRAY<STRING>,
  estimated_cost_inr FLOAT64 NOT NULL,
  verifier_status STRING NOT NULL,
  idempotency_key STRING NOT NULL
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "Agent diagnostic intervention proposals"
);

CREATE TABLE IF NOT EXISTS `ops.work_orders` (
  work_order_id STRING NOT NULL,
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  created_at TIMESTAMP NOT NULL,
  idempotency_key STRING NOT NULL,
  status STRING NOT NULL,
  urgency STRING NOT NULL,
  diagnosed_cause STRING NOT NULL,
  confidence_score FLOAT64 NOT NULL,
  crew_instructions_en STRING NOT NULL,
  crew_instructions_hi STRING NOT NULL,
  recommended_actions ARRAY<STRING>,
  required_equipment ARRAY<STRING>,
  estimated_person_days INT64 NOT NULL,
  estimated_cost_inr FLOAT64 NOT NULL,
  dfo_approval_required BOOL NOT NULL,
  assigned_beat_guard STRING,
  contact_phone STRING,
  dispatch_payload JSON
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "Verified field work orders dispatched to beat crews"
);

-- -----------------------------------------------------------------------------
-- DATASET: audit
-- Audit logs: deterministic policy evaluations and agent decision traces
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `audit.policy_evaluations` (
  evaluation_id STRING NOT NULL,
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  evaluated_at TIMESTAMP NOT NULL,
  intervention_id STRING NOT NULL,
  is_valid BOOL NOT NULL,
  passed_rules ARRAY<STRING>,
  violated_rules ARRAY<STRING>,
  rule_explanations STRING,
  overridden_cause STRING,
  dfo_approval_required BOOL NOT NULL
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "Deterministic policy verifier evaluation history"
);

CREATE TABLE IF NOT EXISTS `audit.decision_logs` (
  log_id STRING NOT NULL,
  site_id STRING NOT NULL,
  date DATE NOT NULL,
  logged_at TIMESTAMP NOT NULL,
  agent_name STRING NOT NULL,
  prompt_summary STRING,
  tool_calls ARRAY<STRUCT<
    tool_name STRING,
    parameters JSON,
    response_summary STRING
  >>,
  reasoning_trace STRING,
  latency_ms INT64
)
PARTITION BY date
CLUSTER BY site_id
OPTIONS (
  require_partition_filter = true,
  description = "ADK agent reasoning and tool invocation traces"
);
