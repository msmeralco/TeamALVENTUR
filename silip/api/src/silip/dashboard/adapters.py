"""Read the exported models' backtest verdict (models/<task>/<name>/metadata.json)."""

from __future__ import annotations

import json
from pathlib import Path


def model_kept(models_dir: Path, task: str, name: str) -> bool | None:
    """The `kept` verdict of an exported model; None for baselines and models without one."""
    path = models_dir / task / name / "metadata.json"
    if not path.exists():
        return None
    kept = json.loads(path.read_text(encoding="utf-8")).get("kept")
    return kept if isinstance(kept, bool) else None
