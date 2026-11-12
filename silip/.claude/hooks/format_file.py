"""PostToolUse (Edit|Write): format the file Claude just edited.

Picks a formatter by extension and runs it if installed. Never blocks: failures go to stderr
and the hook always exits 0.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB = PROJECT_ROOT / "web"
PRETTIER_SUFFIXES = {".ts", ".tsx", ".css", ".json", ".html"}
SKIPPED_DIRS = {".venv", "node_modules", ".terraform", ".pio"}


def formatter_command(path: Path) -> list[str] | None:
    """Return the formatter command for a file, or None if it needs no formatting."""
    if not path.is_relative_to(PROJECT_ROOT) or SKIPPED_DIRS.intersection(path.parts):
        return None
    if path.suffix == ".py" and (uv := shutil.which("uv")):
        return [uv, "run", "--project", str(PROJECT_ROOT), "ruff", "format", str(path)]
    if path.suffix in {".tf", ".tfvars"} and (terraform := shutil.which("terraform")):
        return [terraform, "fmt", str(path)]
    if (
        path.suffix in PRETTIER_SUFFIXES
        and path.is_relative_to(WEB)
        and (WEB / "node_modules" / ".bin").exists()
        and (npx := shutil.which("npx"))
    ):
        return [npx, "--no-install", "prettier", "--write", str(path)]
    return None


def main() -> int:
    try:
        file_path = json.load(sys.stdin).get("tool_input", {}).get("file_path")
        command = formatter_command(Path(file_path).resolve()) if file_path else None
        if command:
            # No shell: argv is a resolved formatter path plus the edited file.
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=50, check=False
            )  # noqa: S603
            if result.returncode != 0:
                print(
                    f"format_file: {Path(command[0]).name} failed:\n{result.stderr}",
                    file=sys.stderr,
                )
    except Exception as error:  # a formatting hook must never block an edit
        print(f"format_file: skipped ({error})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
