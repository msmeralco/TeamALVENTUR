# AGENTS.md

Shared guide for every coding agent (Claude Code, Codex, Cursor) and every human on SILIP. What SILIP is and the commands: [CLAUDE.md](CLAUDE.md). Product spec: [docs/SPEC.md](docs/SPEC.md).

## Rules (defined once, here)
- [Engineering standards](.agents/rules/engineering-standards.md): KISS, DRY, SOLID, CLEAN, strategy pattern, definition of done
- [Python](.agents/rules/python.md): uv, ruff, pyright, feature layers, `ml/` vs `api/`
- [TypeScript / web](.agents/rules/typescript-web.md): Vite, React, generated client, feature folders
- [Terraform](.agents/rules/terraform.md): modules + envs, Neon, no VPC, never apply without a human
- [Firmware](.agents/rules/iot-firmware.md): measure only, payload contract, secrets.h
- [Security and privacy](.agents/rules/security-privacy.md): sin_hash, is_simulated, Cognito, secrets
- [Git workflow](.agents/rules/git-workflow.md): dev branch, `type(scope): description`, no AI attribution

Claude Code skills and subagents live in `.claude/` and link to these rules instead of repeating them.
