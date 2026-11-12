terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }

  # Local state until a shared backend exists. For a team, add an S3 backend with locking and keep
  # its values in an untracked backend.hcl.
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = var.project
      Environment = local.environment
      ManagedBy   = "terraform"
    }
  }
}
