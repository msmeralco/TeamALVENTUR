variable "name" {
  type        = string
  description = "Name prefix, e.g. silip-dev."
}

variable "image_tag" {
  type        = string
  description = "Tag of the API image in this module's ECR repository (pushed before apply)."
}

variable "architecture" {
  type        = string
  description = "Lambda CPU architecture; the image must be built for it."
  default     = "x86_64"
  validation {
    condition     = contains(["arm64", "x86_64"], var.architecture)
    error_message = "architecture must be arm64 or x86_64."
  }
}

variable "api_memory_mb" {
  type        = number
  description = "API Lambda memory. In DB mode the API only reads stored risk scores (the score Lambda fits models)."
  default     = 1024
}

variable "scoring_memory_mb" {
  type        = number
  description = "Score Lambda memory. Measured peak 642 MB for 2,000 transformers x 14 days locally."
  default     = 2048
}

variable "scoring_schedule" {
  type        = string
  description = "EventBridge schedule for the score Lambda; matches the 15-min clamp interval in iot/include/config.h."
  default     = "rate(15 minutes)"
}

variable "data_source" {
  type        = string
  description = "DataSource strategy for the API."
  default     = "clamp"
  validation {
    condition     = contains(["simulated", "clamp", "smart_meter"], var.data_source)
    error_message = "data_source must be simulated, clamp or smart_meter."
  }
}

variable "mobile_poc_device_ids" {
  type        = set(string)
  description = "Public mobile PoC IDs. Leave empty outside the demo environment."
  default     = []
}

variable "weather_source" {
  type        = string
  description = "Weather strategy for scoring (ADR 0006). open_meteo needs no key, secret or IAM; Lambdas already have egress."
  default     = "open_meteo"
  validation {
    condition     = contains(["simulated", "open_meteo"], var.weather_source)
    error_message = "weather_source must be simulated or open_meteo."
  }
}

variable "open_meteo_base_url" {
  type        = string
  description = "Open-Meteo forecast endpoint, without a trailing slash."
  default     = "https://api.open-meteo.com/v1/forecast"
  validation {
    condition     = can(regex("^https://[^/]+(/.*[^/])?$", var.open_meteo_base_url))
    error_message = "open_meteo_base_url must be an https URL without a trailing slash."
  }
}

variable "strategies" {
  type        = map(string)
  description = "Model strategy env vars, e.g. { FORECASTER = \"lightgbm\" }."
  default     = {}
}

variable "cognito_user_pool_id" {
  type        = string
  description = "Cognito user pool the API trusts."
}

variable "cognito_client_id" {
  type        = string
  description = "Cognito app client whose access tokens the API accepts."
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention."
  default     = 7
}

variable "secret_recovery_days" {
  type        = number
  description = "Days a deleted secret can be restored (0 deletes at once)."
  default     = 7
}

variable "force_delete_images" {
  type        = bool
  description = "Allow destroying the ECR repository with images in it (dev only)."
  default     = false
}
