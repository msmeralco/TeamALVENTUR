variable "name" {
  type        = string
  description = "Name prefix, e.g. silip-dev."
}

variable "api_function_url" {
  type        = string
  description = "API Lambda function URL (https://...lambda-url...on.aws/)."
}

variable "api_function_name" {
  type        = string
  description = "API Lambda name; CloudFront is granted permission to invoke it."
}

variable "price_class" {
  type        = string
  description = "CloudFront price class. PriceClass_200 includes Asia edge locations."
  default     = "PriceClass_200"
  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.price_class)
    error_message = "price_class must be PriceClass_100, PriceClass_200 or PriceClass_All."
  }
}

variable "force_destroy" {
  type        = bool
  description = "Allow destroying the bucket with files in it (dev only)."
  default     = false
}
