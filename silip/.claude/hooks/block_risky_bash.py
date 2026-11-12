"""PreToolUse (Bash): block destructive or pipe-to-shell commands. Exit 2 asks the user first."""

from __future__ import annotations

import json
import re
import sys

RISKY = re.compile(
    r"rm\s+-rf\s+[/~]"
    r"|git\s+reset\s+--hard"
    r"|git\s+push\s+(-f|--force)"
    r"|\|\s*(sh|bash)\b"
    r"|terraform\s+(destroy|state\s+rm)"
)


def main() -> int:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if RISKY.search(command):
        print("Blocked: destructive or unsafe command. Ask the user first.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
