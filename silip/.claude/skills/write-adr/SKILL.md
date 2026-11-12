---
name: write-adr
description: Record an architecture decision in docs/adr/. Use when choosing between technologies or approaches (a model, a data source, a cloud service, an auth flow), or when reversing an earlier decision.
---

1. Copy `docs/adr/template.md` to `docs/adr/NNNN-short-title.md` (next number, kebab-case).
2. Fill in context, decision, alternatives considered, and consequences. Under one page.
3. If it replaces an older ADR, set the old one's status to `Superseded by NNNN`. Never delete it.
4. If it changes the architecture, update `docs/SPEC.md#architecture` in the same change.
5. Numbers follow the project rule: cite `docs/SPEC.md#sources` or mark `[VERIFY]`.
