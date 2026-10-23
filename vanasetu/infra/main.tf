# VanaSetu GCP Infrastructure Definition (Terraform)
# ======================================================
# Provisions BigQuery partitioned datasets, Cloud Storage for satellite scenes,
# Pub/Sub alert queues, Cloud Run agent microservice, and Cloud Scheduler.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.20"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ------------------------------------------------------------------------------
# 1. BigQuery Dataset & Partitioned Tables
# ------------------------------------------------------------------------------

resource "google_bigquery_dataset" "monitoring_dataset" {
  dataset_id                  = var.bigquery_dataset_name
  friendly_name               = "VanaSetu Forest Restoration Monitoring"
  description                 = "Contains parcel registries, Sentinel-2 vegetation indices, IMD weather, active fire telemetry, and field work orders"
  location                    = var.region
  default_table_expiration_ms = null # Retain historical forest time-series permanently

  labels = {
    application = "vanasetu"
    environment = var.environment
    domain      = "forestry-conservation"
  }
}

# Table: Parcels Registry
resource "google_bigquery_table" "parcels_table" {
  dataset_id = google_bigquery_dataset.monitoring_dataset.dataset_id
  table_id   = "parcels"
  schema     = jsonencode([
    { name = "parcel_id", type = "STRING", mode = "REQUIRED", description = "Unique Parcel ID" },
    { name = "state", type = "STRING", mode = "REQUIRED" },
    { name = "district", type = "STRING", mode = "REQUIRED" },
    { name = "forest_division", type = "STRING", mode = "REQUIRED" },
    { name = "range_name", type = "STRING", mode = "REQUIRED" },
    { name = "beat_name", type = "STRING", mode = "REQUIRED" },
    { name = "latitude", type = "FLOAT", mode = "REQUIRED" },
    { name = "longitude", type = "FLOAT", mode = "REQUIRED" },
    { name = "area_hectares", type = "FLOAT", mode = "REQUIRED" },
    { name = "plantation_date", type = "STRING", mode = "REQUIRED" },
    { name = "afforestation_scheme", type = "STRING", mode = "NULLABLE" },
    { name = "species_mix", type = "RECORD", mode = "REPEATED", fields = [
      { name = "species_name", type = "STRING", mode = "REQUIRED" },
      { name = "common_name", type = "STRING", mode = "REQUIRED" },
      { name = "count", type = "INTEGER", mode = "REQUIRED" },
      { name = "is_deciduous", type = "BOOLEAN", mode = "REQUIRED" },
      { name = "drought_tolerance", type = "STRING", mode = "NULLABLE" }
    ]},
    { name = "soil_type", type = "STRING", mode = "NULLABLE" },
    { name = "irrigation_type", type = "STRING", mode = "NULLABLE" },
    { name = "fencing_type", type = "STRING", mode = "NULLABLE" },
    { name = "assigned_officer", type = "STRING", mode = "NULLABLE" },
    { name = "officer_phone", type = "STRING", mode = "NULLABLE" }
  ])
}

# Table: Vegetation Telemetry (Partitioned by timestamp, Clustered by parcel_id)
resource "google_bigquery_table" "vegetation_telemetry_table" {
  dataset_id = google_bigquery_dataset.monitoring_dataset.dataset_id
  table_id   = "vegetation_telemetry"

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  clustering = ["parcel_id"]

  schema = jsonencode([
    { name = "parcel_id", type = "STRING", mode = "REQUIRED" },
    { name = "timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "ndvi", type = "FLOAT", mode = "REQUIRED" },
    { name = "ndwi", type = "FLOAT", mode = "REQUIRED" },
    { name = "evi", type = "FLOAT", mode = "NULLABLE" },
    { name = "cloud_cover_pct", type = "FLOAT", mode = "REQUIRED" },
    { name = "baseline_ndvi_mean", type = "FLOAT", mode = "REQUIRED" },
    { name = "baseline_ndvi_std", type = "FLOAT", mode = "REQUIRED" },
    { name = "ndvi_drop_pct", type = "FLOAT", mode = "REQUIRED" },
    { name = "z_score", type = "FLOAT", mode = "REQUIRED" },
    { name = "is_anomaly", type = "BOOLEAN", mode = "REQUIRED" }
  ])
}

# Table: Work Orders (Partitioned by creation time, Clustered by urgency & status)
resource "google_bigquery_table" "work_orders_table" {
  dataset_id = google_bigquery_dataset.monitoring_dataset.dataset_id
  table_id   = "work_orders"

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  clustering = ["urgency", "status"]

  schema = jsonencode([
    { name = "work_order_id", type = "STRING", mode = "REQUIRED" },
    { name = "parcel_id", type = "STRING", mode = "REQUIRED" },
    { name = "created_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "status", type = "STRING", mode = "REQUIRED" },
    { name = "urgency", type = "STRING", mode = "REQUIRED" },
    { name = "diagnosed_cause", type = "STRING", mode = "REQUIRED" },
    { name = "confidence_score", type = "FLOAT", mode = "REQUIRED" },
    { name = "crew_instructions_en", type = "STRING", mode = "REQUIRED" },
    { name = "crew_instructions_hi", type = "STRING", mode = "REQUIRED" },
    { name = "recommended_actions", type = "STRING", mode = "REPEATED" },
    { name = "required_equipment", type = "STRING", mode = "REPEATED" },
    { name = "estimated_person_days", type = "INTEGER", mode = "REQUIRED" },
    { name = "estimated_cost_inr", type = "FLOAT", mode = "REQUIRED" },
    { name = "dfo_approval_required", type = "BOOLEAN", mode = "REQUIRED" },
    { name = "assigned_beat_guard", type = "STRING", mode = "NULLABLE" },
    { name = "contact_phone", type = "STRING", mode = "NULLABLE" }
  ])
}

# ------------------------------------------------------------------------------
# 2. Cloud Storage: Satellite Scenes & Surveyor Attachments
# ------------------------------------------------------------------------------

resource "google_storage_bucket" "satellite_bucket" {
  name                        = "${var.storage_bucket_prefix}-${var.environment}-${var.project_id}"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    application = "vanasetu"
    environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# 3. Pub/Sub Topics: Telemetry Alerts & Work Order Dispatch
# ------------------------------------------------------------------------------

resource "google_pubsub_topic" "anomaly_alerts_topic" {
  name = "vanasetu-telemetry-anomalies"
  labels = {
    environment = var.environment
  }
}

resource "google_pubsub_topic" "work_orders_topic" {
  name = "vanasetu-work-orders-dispatched"
  labels = {
    environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# 4. Service Account & IAM Least-Privilege Permissions
# ------------------------------------------------------------------------------

resource "google_service_account" "vanasetu_agent_sa" {
  account_id   = "vanasetu-agent-runner"
  display_name = "VanaSetu Multi-Agent System Runner"
}

resource "google_project_iam_member" "bigquery_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.vanasetu_agent_sa.email}"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.vanasetu_agent_sa.email}"
}

resource "google_project_iam_member" "storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.vanasetu_agent_sa.email}"
}

resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.vanasetu_agent_sa.email}"
}

# ------------------------------------------------------------------------------
# 5. Cloud Run Service (Hosting VanaSetu ADK Multi-Agent Service)
# ------------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "vanasetu_service" {
  name     = "vanasetu-agent-service"
  location = var.region

  template {
    service_account = google_service_account.vanasetu_agent_sa.email

    containers {
      image = "gcr.io/${var.project_id}/vanasetu-agent:latest"

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = google_bigquery_dataset.monitoring_dataset.dataset_id
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
  }
}

# ------------------------------------------------------------------------------
# 6. Cloud Scheduler: Daily Anomaly Monitoring Trigger (06:00 IST)
# ------------------------------------------------------------------------------

resource "google_cloud_scheduler_job" "daily_monitoring_job" {
  name             = "vanasetu-daily-monitoring-trigger"
  description      = "Triggers daily Sentinel-2 and IMD weather ingestion at 06:00 IST"
  schedule         = "30 0 * * *" # 00:30 UTC = 06:00 IST
  time_zone        = "Asia/Kolkata"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.vanasetu_service.uri}/pipeline/run-daily"

    oidc_token {
      service_account_email = google_service_account.vanasetu_agent_sa.email
    }
  }
}
