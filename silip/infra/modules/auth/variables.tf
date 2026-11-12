variable "name" {
  type        = string
  description = "Name prefix, e.g. silip-dev."
}

variable "domain_prefix" {
  type        = string
  description = "Globally unique prefix for the Cognito managed login domain."
}

variable "web_origins" {
  type        = list(string)
  description = "Origins allowed for sign-in callbacks and sign-out, e.g. http://localhost:5173."
}

variable "deletion_protection" {
  type        = bool
  description = "Protect the user pool from deletion (on in prod)."
  default     = false
}
