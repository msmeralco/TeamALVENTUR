# Terraform rules (`infra/`)

On top of [engineering-standards.md](engineering-standards.md).

## Structure
- `infra/modules/<name>/` with `main.tf`, `variables.tf`, `outputs.tf`. One module = one concern: `auth` (Cognito), `ingest` (IoT Core), `api` (Lambda + function URL), `web` (S3 + CloudFront).
- `infra/envs/{dev,prod}/` only wire modules. Differences live in `terraform.tfvars` (untracked; copy `terraform.tfvars.example`).
- No single-resource wrapper modules unless they add defaults we always want.

## Conventions
- Names `${var.project}-${var.environment}-<purpose>`, built once in `locals`.
- Tags via the provider's `default_tags`.
- Every variable has `type` and `description` (validation for enums). Every output has `description`.
- Pin providers (`~>`) and `required_version`. No hardcoded region or account: `var.region`.

## Security and cost
- Least-privilege IAM; no `*` actions; comment any unavoidable `Resource = "*"`.
- No secrets in `.tf`, `.tfvars` or non-`sensitive` outputs. The Neon project exists outside Terraform; its URL goes into Secrets Manager by hand, never into state.
- Serverless and free tiers first: no VPC, no NAT, no RDS (the database is Neon). Log retention 7 days in dev.

## Workflow
- `terraform fmt -recursive` and `terraform validate` must pass.
- **Never run `terraform apply`, `destroy`, `import` or `state` without explicit human approval.** Show the plan first.
