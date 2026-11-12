# Git workflow

## Branches
```
main  <- releases only (merged from dev)
 └─ dev  <- all work lands here first
     └─ feat/<topic>, fix/<topic>, chore/<topic>
```

## Commit messages
`type(scope): description`
- type: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`, `build`, `ci`
- scope: `ml`, `api`, `web`, `iot`, `infra`, `data`, `docs`, `repo`
- description: imperative, lowercase, no period, 72 characters max. Example: `feat(ml): add dbscan outage locator`.

## No AI tool attribution
No AI `Co-Authored-By` lines, "Generated with ..." footers, or tool names in commits, PRs or code comments.

## Hygiene
- Small commits that each pass `make test`.
- Never commit `.env`, `terraform.tfvars`, `*.tfstate`, `iot/include/secrets.h`, `data/raw/` or real household data.
- Agents never commit, push or merge without explicit human approval.
