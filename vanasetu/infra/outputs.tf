# VanaSetu Terraform Outputs

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID hosting plantation telemetry"
  value       = google_bigquery_dataset.monitoring_dataset.dataset_id
}

output "storage_bucket_url" {
  description = "GCS bucket for satellite scenes and field photos"
  value       = google_storage_bucket.satellite_bucket.url
}

output "anomaly_topic_id" {
  description = "Pub/Sub topic ID for vegetation anomaly alerts"
  value       = google_pubsub_topic.anomaly_alerts_topic.id
}

output "work_orders_topic_id" {
  description = "Pub/Sub topic ID for dispatched work orders"
  value       = google_pubsub_topic.work_orders_topic.id
}

output "cloud_run_service_url" {
  description = "HTTPS endpoint of the VanaSetu Cloud Run Agent Service"
  value       = google_cloud_run_v2_service.vanasetu_service.uri
}

output "service_account_email" {
  description = "Service account running the agent orchestration workloads"
  value       = google_service_account.vanasetu_agent_sa.email
}
