# VanaSetu GCP Infrastructure Variables

variable "project_id" {
  description = "Google Cloud Project ID where VanaSetu resources will be provisioned"
  type        = string
  default     = "vanasetu-forest-monitoring"
}

variable "region" {
  description = "GCP Region for regional resources (e.g. asia-south1 for Mumbai, India)"
  type        = string
  default     = "asia-south1"
}

variable "zone" {
  description = "GCP Zone for compute resources"
  type        = string
  default     = "asia-south1-a"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "bigquery_dataset_name" {
  description = "Name of the primary BigQuery dataset"
  type        = string
  default     = "vanasetu_monitoring"
}

variable "storage_bucket_prefix" {
  description = "Prefix for GCS bucket storing satellite scenes and drone imagery"
  type        = string
  default     = "vanasetu-earth-observation"
}

variable "alert_notification_email" {
  description = "Email address for critical forest fire and drought alerts"
  type        = string
  default     = "beat-officer-alerts@vanasetu.nic.in"
}
