---
name: deploy
description: Deploy SILIP to AWS with Terraform (Neon, Cognito, IoT Core, API Lambda, S3 + CloudFront) for one environment. Run only when the user asks to deploy.
disable-model-invocation: true
argument-hint: "[dev|prod, default dev]"
---

Deploy environment `$ARGUMENTS` (default `dev`). Commands run from the repo root. `ENV=infra/envs/<env>`.

1. Preconditions. Stop and report if any fail:
   - `make lint test` passes; `cd web && npm run build` passes.
   - `terraform -chdir=$ENV init` and `terraform -chdir=$ENV validate` pass.
   - `NEON_API_KEY` and AWS credentials are set in the shell (never print them).
   - `$ENV/terraform.tfvars` exists (copied from the example).
2. The `infra-reviewer` subagent reports "OK to plan".
3. `terraform -chdir=$ENV plan -out=tfplan`. Show the user the summary (adds, changes, destroys) and **wait for approval**.
4. `terraform -chdir=$ENV apply tfplan`.
5. Build and upload: the API image (`api/Dockerfile.lambda`) and `web/dist` to the bucket from `terraform output -raw web_bucket`, then invalidate CloudFront.
6. Apply `db/schema.sql` to the Neon branch for this env.
7. Smoke test: `curl $(terraform -chdir=$ENV output -raw web_url)/api/health`.
8. Record outputs (web URL, Cognito pool ID, image tag) in `docs/deploy.md`.

Guardrails: no VPC or NAT; log retention 7 days in dev; never print secrets or Terraform state; prod needs a separate explicit go-ahead.
