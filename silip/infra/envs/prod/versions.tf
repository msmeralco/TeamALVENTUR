terraform {
  required_version = ">= 1.10" # S3 native state locking (use_lockfile)

  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }

  # Shared state in S3 with native locking. Bucket, key and region live in an untracked
  # backend.hcl (copy backend.hcl.example): terraform init -backend-config=backend.hcl
  backend "s3" {}
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
