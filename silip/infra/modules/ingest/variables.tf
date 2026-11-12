variable "name" {
  type        = string
  description = "Name prefix, e.g. silip-dev."
}

variable "ingest_function_arn" {
  type        = string
  description = "Lambda that validates and stores each reading."
}

variable "ingest_function_name" {
  type        = string
  description = "Name of the same Lambda, for the invoke permission."
}
