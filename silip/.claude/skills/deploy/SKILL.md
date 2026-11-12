---
name: deploy
description: Deploy SILIP to AWS with Terraform (Cognito, IoT Core, API Lambda, S3 + CloudFront) for one environment. Run only when the user asks to deploy.
disable-model-invocation: true
argument-hint: "[dev|prod, default dev]"
---

Deploy environment `$ARGUMENTS` (default `dev`). Commands run from the repo root. `ENV=infra/envs/<env>`.

1. Preconditions. Stop and report if any fail:
   - `make lint test` passes; `cd web && npm run build` passes.
   - `terraform -chdir=$ENV init` and `terraform -chdir=$ENV validate` pass.
   - AWS credentials are set in the shell (never print them).
   - `$ENV/terraform.tfvars` exists (copied from the example).
2. The `infra-reviewer` subagent reports "OK to plan".
3. `terraform -chdir=$ENV plan -out=tfplan`. Show the user the summary (adds, changes, destroys) and **wait for approval**.
4. `terraform -chdir=$ENV apply tfplan`.
5. Build and upload:
   - API image: `docker buildx build --platform linux/amd64 --provenance=false -f api/Dockerfile.lambda -t <ecr>:<new tag> --push .` (tags are immutable; bump the tag).
   - Web: build from committed code with the `VITE_COGNITO_*` values from `terraform output`, then upload each file to `terraform output -raw web_bucket` with an explicit `--content-type` (`application/javascript`, `text/css`, `text/html`). On Windows, `aws s3 sync` guesses `.js` as `text/plain` and the browser refuses to run it. `index.html` gets `Cache-Control: no-cache`; hashed assets get `immutable`.
   - Invalidate CloudFront `/*`.
6. First deploy only: put the Neon pooled URL into the secret (`terraform output -raw database_secret_arn`) with `aws secretsmanager put-secret-value`. Apply `db/schema.sql` with `make db` (uses `DATABASE_DIRECT_URL`).
7. Smoke test: `curl $(terraform -chdir=$ENV output -raw web_url)/api/health`.
8. Record outputs (web URL, Cognito pool ID, image tag) in `docs/deploy.md`.

Guardrails: no VPC or NAT; log retention 7 days in dev; never print secrets or Terraform state; prod needs a separate explicit go-ahead.
