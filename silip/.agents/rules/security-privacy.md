# Security and privacy rules

- **SINs only as salted hashes (`sin_hash`).** Never raw SINs in code, data, logs, fixtures, URLs or tokens. Hashing lives in `silip_ml.core.privacy` only.
- **Simulated data is labeled `is_simulated`** in every row, API response, UI view and report.
- **RA 10173:** households opt in. Engineer views show transformer totals, never one household's usage.
- **Auth (Cognito, see `docs/auth-contract.md`):** invite-only. Groups `engineers` and `households`. A household's `sin_hash` is looked up server-side from the token's `sub` (`household_account` table), never taken from the request. `AUTH_DISABLED=true` is refused inside Lambda.
- **Secrets:** never in code, git, logs, prompts or `VITE_*`. Local secrets in `.env` (git-ignored); deployed secrets in Secrets Manager.
- **Least privilege** IAM; one role per function.
- **Logs:** no tokens, no `DATABASE_URL`, no per-household readings at INFO.
- Report an accidental secret commit at once: rotate first, then rewrite history.
