"""PreToolUse (Edit|Write): block raw SINs and edits to secrets, state, raw data and lockfiles.

Exit 2 sends the reason back to Claude. Any other failure lets the edit through, so the hook
never wedges a session; the patterns below are the whole policy.
"""

from __future__ import annotations

import json
import re
import sys

BLOCKED_PATHS = re.compile(
    r"(^|[\\/])("
    r"\.env(\..+)?"  # .env, .env.local (but not .env.example, allowed below)
    r"|terraform\.tfvars"
    r"|.*\.tfstate(\..+)?"
    r"|\.terraform\.lock\.hcl"
    r"|uv\.lock|package-lock\.json"
    r"|secrets\.h"
    r")$"
    r"|(^|[\\/])data[\\/]raw[\\/]",
    re.IGNORECASE,
)
ALLOWED_EXAMPLES = re.compile(r"\.example(\.[a-z]+)?$", re.IGNORECASE)
RAW_SIN = re.compile(r"""["']?\bsin\b["']?\s*[:=]\s*["']?\d{8,}""", re.IGNORECASE)


def written_text(tool_input: dict) -> str:
    parts = [tool_input.get("content") or "", tool_input.get("new_string") or ""]
    parts += [edit.get("new_string") or "" for edit in tool_input.get("edits") or []]
    return "\n".join(parts)


def main() -> int:
    tool_input = json.load(sys.stdin).get("tool_input", {})
    path = tool_input.get("file_path") or ""
    if BLOCKED_PATHS.search(path) and not ALLOWED_EXAMPLES.search(path):
        print(
            f"Blocked: {path} is a secret, state, raw data or lockfile. "
            "Change code or config instead (uv add, npm install, terraform init).",
            file=sys.stderr,
        )
        return 2
    if RAW_SIN.search(written_text(tool_input)):
        print("Blocked: raw SIN. Use sin_hash (silip_ml.core.privacy).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
