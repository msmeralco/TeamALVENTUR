variable "project" {
  type        = string
  description = "Project name used in resource names and tags."
  default     = "silip"
}

variable "region" {
  type        = string
  description = "AWS region for every regional resource."
  default     = "ap-southeast-1"
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Globally unique prefix for the Cognito managed login domain (the env name is appended)."
}

variable "web_domain" {
  type        = string
  description = "CloudFront domain (terraform output web_domain). Null on the first apply, then set and apply again."
  default     = null
}

variable "image_tag" {
  type        = string
  description = "API image tag pushed to the ECR repository."
}

variable "data_source" {
  type        = string
  description = "DataSource strategy: simulated, clamp or smart_meter."
  default     = "clamp"
}

variable "weather_source" {
  type        = string
  description = "Weather strategy for scoring: simulated or open_meteo (ADR 0006)."
  default     = "open_meteo"
}

variable "open_meteo_base_url" {
  type        = string
  description = "Open-Meteo forecast endpoint, without a trailing slash."
  default     = "https://api.open-meteo.com/v1/forecast"
}

variable "strategies" {
  type        = map(string)
  description = "Model strategies, e.g. { FORECASTER = \"lightgbm\" }. Empty means baselines."
  default     = {}
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days."
  default     = 7
}

variable "protect_resources" {
  type        = bool
  description = "Deletion protection and no force-destroy. Off in dev, on in prod."
  default     = false
}
