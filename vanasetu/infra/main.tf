# ==============================================================================
# VanaSetu Complete Google Cloud Infrastructure (Terraform)
# Target Region: asia-south1 (Mumbai, India)
# All resources constrained strictly to asia-south1.
# Enforces least-privilege IAM, required partition filters, and Secret Manager.
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.25"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.25"
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
# 1. API Enablement (Paused for User Approval)
# ------------------------------------------------------------------------------

locals {
  required_apis = [
    "aiplatform.googleapis.com",       # Vertex AI
    "bigquery.googleapis.com",         # BigQuery
    "run.googleapis.com",              # Cloud Run
    "cloudbuild.googleapis.com",       # Cloud Build
    "artifactregistry.googleapis.com", # Artifact Registry
    "pubsub.googleapis.com",           # Pub/Sub
    "cloudtasks.googleapis.com",       # Cloud Tasks
    "firestore.googleapis.com",        # Firestore
    "secretmanager.googleapis.com",    # Secret Manager
    "cloudscheduler.googleapis.com"    # Cloud Scheduler
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each                   = toset(local.required_apis)
  project                    = var.project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Artifact Registry Docker Repository
resource "google_artifact_registry_repository" "docker_repo" {
  provider      = google-beta
  project       = var.project_id
  location      = var.region
  repository_id = "vanasetu-docker-repo"
  description   = "Docker container images for VanaSetu Cloud Run workers and agents"
  format        = "DOCKER"

  depends_on = [google_project_service.enabled_apis]
}

# ------------------------------------------------------------------------------
# 2. IAM Service Accounts (Least Privilege Scopes)
# ------------------------------------------------------------------------------

# Service Account 1: vanasetu-ingest (write access to raw BigQuery tables only)
resource "google_service_account" "sa_ingest" {
  account_id   = "vanasetu-ingest"
  display_name = "VanaSetu Telemetry Ingestion Service Account"
}

# Service Account 2: vanasetu-agent (read core, write interventions, call Gemini)
resource "google_service_account" "sa_agent" {
  account_id   = "vanasetu-agent"
  display_name = "VanaSetu ADK Multi-Agent Runtime Service Account"
}

# Service Account 3: vanasetu-dispatcher (read interventions, write work_orders only)
resource "google_service_account" "sa_dispatcher" {
  account_id   = "vanasetu-dispatcher"
  display_name = "VanaSetu Work Order Dispatcher Service Account"
}

# Service Account 4: vanasetu-dashboard (read-only across datasets)
resource "google_service_account" "sa_dashboard" {
  account_id   = "vanasetu-dashboard"
  display_name = "VanaSetu Looker Studio and Ops Dashboard Service Account"
}

# Project-level role: BigQuery Job User (needed by all to run queries)
resource "google_project_iam_member" "sa_ingest_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.sa_ingest.email}"
}

resource "google_project_iam_member" "sa_agent_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.sa_agent.email}"
}

resource "google_project_iam_member" "sa_dispatcher_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.sa_dispatcher.email}"
}

resource "google_project_iam_member" "sa_dashboard_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.sa_dashboard.email}"
}

# Vertex AI Model User for vanasetu-agent to invoke Gemini
resource "google_project_iam_member" "sa_agent_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.sa_agent.email}"
}

# ------------------------------------------------------------------------------
# 3. BigQuery Datasets & Tables (core, ops, audit)
# ------------------------------------------------------------------------------

# Dataset: core
resource "google_bigquery_dataset" "core" {
  dataset_id                  = "core"
  friendly_name               = "VanaSetu Core Datasets"
  description                 = "Plantation site registries, Sentinel-2 indices, IMD weather, active fire telemetry"
  location                    = var.region
  default_table_expiration_ms = null

  depends_on = [google_project_service.enabled_apis]
}

# Dataset: ops
resource "google_bigquery_dataset" "ops" {
  dataset_id                  = "ops"
  friendly_name               = "VanaSetu Operations"
  description                 = "Proposed agent interventions and verified field work orders"
  location                    = var.region
  default_table_expiration_ms = null

  depends_on = [google_project_service.enabled_apis]
}

# Dataset: audit
resource "google_bigquery_dataset" "audit" {
  dataset_id                  = "audit"
  friendly_name               = "VanaSetu Audit Trail"
  description                 = "Deterministic policy evaluations and agent tool-call decision logs"
  location                    = var.region
  default_table_expiration_ms = null

  depends_on = [google_project_service.enabled_apis]
}

# --- Dataset-level IAM Roles ---

# vanasetu-ingest: write access to core tables only
resource "google_bigquery_dataset_iam_member" "ingest_core_editor" {
  dataset_id = google_bigquery_dataset.core.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.sa_ingest.email}"
}

# vanasetu-agent: read core tables
resource "google_bigquery_dataset_iam_member" "agent_core_viewer" {
  dataset_id = google_bigquery_dataset.core.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.sa_agent.email}"
}

# vanasetu-agent: write access to ops
resource "google_bigquery_dataset_iam_member" "agent_ops_editor" {
  dataset_id = google_bigquery_dataset.ops.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.sa_agent.email}"
}

# vanasetu-dispatcher: read and write to ops (read interventions, write work orders)
resource "google_bigquery_dataset_iam_member" "dispatcher_ops_editor" {
  dataset_id = google_bigquery_dataset.ops.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.sa_dispatcher.email}"
}

# vanasetu-dashboard: read-only across core, ops, audit
resource "google_bigquery_dataset_iam_member" "dashboard_core_viewer" {
  dataset_id = google_bigquery_dataset.core.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.sa_dashboard.email}"
}

resource "google_bigquery_dataset_iam_member" "dashboard_ops_viewer" {
  dataset_id = google_bigquery_dataset.ops.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.sa_dashboard.email}"
}

resource "google_bigquery_dataset_iam_member" "dashboard_audit_viewer" {
  dataset_id = google_bigquery_dataset.audit.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.sa_dashboard.email}"
}

# --- Core Tables with Partitioning, Clustering & require_partition_filter ---

resource "google_bigquery_table" "core_sites" {
  dataset_id = google_bigquery_dataset.core.dataset_id
  table_id   = "sites"
  schema     = file("${path.module}/schemas/sites.json")
}

resource "google_bigquery_table" "core_satellite_telemetry" {
  dataset_id               = google_bigquery_dataset.core.dataset_id
  table_id                 = "satellite_telemetry"
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["site_id"]
  schema     = file("${path.module}/schemas/satellite_telemetry.json")
}

resource "google_bigquery_table" "core_weather_observations" {
  dataset_id               = google_bigquery_dataset.core.dataset_id
  table_id                 = "weather_observations"
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["site_id"]
  schema     = file("${path.module}/schemas/weather_observations.json")
}

resource "google_bigquery_table" "core_fire_events" {
  dataset_id               = google_bigquery_dataset.core.dataset_id
  table_id                 = "fire_events"
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["site_id"]
  schema     = file("${path.module}/schemas/fire_events.json")
}

# --- Ops Tables ---

resource "google_bigquery_table" "ops_interventions" {
  dataset_id               = google_bigquery_dataset.ops.dataset_id
  table_id                 = "interventions"
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["site_id"]
  schema     = file("${path.module}/schemas/interventions.json")
}

resource "google_bigquery_table" "ops_work_orders" {
  dataset_id               = google_bigquery_dataset.ops.dataset_id
  table_id                 = "work_orders"
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["site_id"]
  schema     = file("${path.module}/schemas/work_orders.json")
}

# --- Audit Tables ---

resource "google_bigquery_table" "audit_policy_evaluations" {
  dataset_id               = google_bigquery_dataset.audit.dataset_id
  table_id                 = "policy_evaluations"
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["site_id"]
  schema     = file("${path.module}/schemas/policy_evaluations.json")
}

# ------------------------------------------------------------------------------
# 4. Cloud Storage Staging Bucket for Vertex AI Agent Engine
# ------------------------------------------------------------------------------

resource "google_storage_bucket" "agent_staging_bucket" {
  name                        = "vanasetu-vertex-staging-${var.project_id}"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_storage_bucket_iam_member" "sa_agent_staging_access" {
  bucket = google_storage_bucket.agent_staging_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.sa_agent.email}"
}

# ------------------------------------------------------------------------------
# 5. Secret Manager for API Keys & Credentials
# ------------------------------------------------------------------------------

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "vanasetu-gemini-api-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_secret_manager_secret_iam_member" "agent_secret_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.sa_agent.email}"
}

# ------------------------------------------------------------------------------
# 6. Cloud Run Private Worker Services & Cloud Scheduler
# ------------------------------------------------------------------------------

# Service 1: Ingestion Worker (under vanasetu-ingest, private access only)
resource "google_cloud_run_v2_service" "ingest_worker" {
  name     = "vanasetu-ingest-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.sa_ingest.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/ingest-worker:latest"

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "BIGQUERY_CORE_DATASET"
        value = google_bigquery_dataset.core.dataset_id
      }
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# Service 2: Dispatch Worker (under vanasetu-dispatcher, private access only)
resource "google_cloud_run_v2_service" "dispatch_worker" {
  name     = "vanasetu-dispatch-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.sa_dispatcher.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/dispatch-worker:latest"

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "BIGQUERY_OPS_DATASET"
        value = google_bigquery_dataset.ops.dataset_id
      }
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# Cloud Scheduler to invoke Nightly Ingestion
resource "google_cloud_scheduler_job" "nightly_ingest_cron" {
  name             = "vanasetu-nightly-ingest-trigger"
  description      = "Nightly trigger for Sentinel-2 satellite and IMD weather ingestion at 02:00 IST"
  schedule         = "30 20 * * *" # 20:30 UTC = 02:00 IST
  time_zone        = "Asia/Kolkata"
  attempt_deadline = "600s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.ingest_worker.uri}/ingest/run-nightly"

    oidc_token {
      service_account_email = google_service_account.sa_ingest.email
    }
  }

  depends_on = [google_project_service.enabled_apis]
}
