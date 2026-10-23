# ==============================================================================
# VanaSetu Terraform Outputs
# ==============================================================================

output "project_id" {
  description = "Target Google Cloud Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region (asia-south1)"
  value       = var.region
}

output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository endpoint"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}

output "service_accounts" {
  description = "Narrowly-scoped least privilege service accounts"
  value = {
    ingest     = google_service_account.sa_ingest.email
    agent      = google_service_account.sa_agent.email
    dispatcher = google_service_account.sa_dispatcher.email
    dashboard  = google_service_account.sa_dashboard.email
  }
}

output "bigquery_datasets" {
  description = "BigQuery datasets configured with date partitions & require_partition_filter"
  value = {
    core  = google_bigquery_dataset.core.dataset_id
    ops   = google_bigquery_dataset.ops.dataset_id
    audit = google_bigquery_dataset.audit.dataset_id
  }
}

output "agent_staging_bucket" {
  description = "Cloud Storage bucket for ADK Agent Engine deployment staging"
  value       = google_storage_bucket.agent_staging_bucket.name
}

output "secret_manager_gemini_key_id" {
  description = "Secret Manager secret ID for Gemini API key"
  value       = google_secret_manager_secret.gemini_api_key.id
}

output "cloud_run_workers" {
  description = "Private Cloud Run worker service endpoints"
  value = {
    ingest_worker   = google_cloud_run_v2_service.ingest_worker.uri
    dispatch_worker = google_cloud_run_v2_service.dispatch_worker.uri
  }
}
