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
  default     = "arm64"
  validation {
    condition     = contains(["arm64", "x86_64"], var.architecture)
    error_message = "architecture must be arm64 or x86_64."
  }
}

variable "api_memory_mb" {
  type        = number
  description = "API Lambda memory. Model fitting runs on cold start."
  default     = 1024
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
