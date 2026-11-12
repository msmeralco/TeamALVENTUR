# infra

Terraform for SILIP on AWS (`ap-southeast-1` by default). The database is an existing Neon project, managed outside Terraform. No VPC, no NAT, no RDS.

- `modules/`: `auth` (Cognito), `api` (Lambda image + function URL + secret; also the `score` Lambda, which EventBridge runs every 15 minutes to write risk scores to Neon, so the API only reads them), `ingest` (IoT Core rule), `web` (S3 + CloudFront, `/api/*` to the Lambda via OAC).
- `envs/dev`, `envs/prod` only wire modules. Copy `terraform.tfvars.example` to `terraform.tfvars`; export AWS credentials. After the first apply, put the Neon pooled URL in the secret from `terraform output database_secret_arn`.
- Check: `terraform -chdir=infra/envs/dev init -backend=false && terraform -chdir=infra/envs/dev validate`. First deploy: apply `-target=module.api.aws_ecr_repository.api`, push the image, then apply all; set `web_domain` from the output and apply again. Deploy only via `/deploy`.

## State
Shared state lives in S3 with native locking (Terraform >= 1.10). The bucket was made once, outside Terraform, with versioning, default encryption, all public access blocked and a TLS-only policy. Each env reads its bucket, key and region from an untracked `backend.hcl`:
```
cp infra/envs/dev/backend.hcl.example infra/envs/dev/backend.hcl   # fill in the bucket name
terraform -chdir=infra/envs/dev init -backend-config=backend.hcl
```
Your AWS user needs s3:ListBucket on the bucket and s3:GetObject, s3:PutObject, s3:DeleteObject on `silip/*` (the lock file is an object next to the state).
