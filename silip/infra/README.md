# infra

Terraform for SILIP on AWS (`ap-southeast-1` by default). The database is an existing Neon project, managed outside Terraform. No VPC, no NAT, no RDS.

- `modules/`: `auth` (Cognito), `api` (Lambda image + function URL + secret), `web` (S3 + CloudFront, `/api/*` to the Lambda via OAC).
- `envs/dev`, `envs/prod` only wire modules. Copy `terraform.tfvars.example` to `terraform.tfvars`; export AWS credentials. After the first apply, put the Neon pooled URL in the secret from `terraform output database_secret_arn`.
- Check: `terraform -chdir=infra/envs/dev init -backend=false && terraform -chdir=infra/envs/dev validate`. First deploy: apply `-target=module.api.aws_ecr_repository.api`, push the image, then apply all; set `web_domain` from the output and apply again. Deploy only via `/deploy`.

Devices send HTTPS directly to the API Lambda. The old `modules/ingest` directory is retained as legacy code and is not wired into either environment. Review resource removals in the Terraform plan when migrating an existing deployment.
