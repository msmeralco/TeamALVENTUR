"""Load a model exported by the notebooks: `models/<task>/<name>/{model.txt, metadata.json}`.

Models are LightGBM native text (never pickle). `metadata.json` holds the feature list and
parameters, so inference never hardcodes a copy of them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import lightgbm as lgb


class ArtifactNotFoundError(FileNotFoundError):
    """No exported model at the expected path."""


@dataclass(frozen=True)
class Artifact:
    """A trained booster and what the notebook recorded about it."""

    booster: lgb.Booster
    metadata: dict[str, Any]  # JSON object; shape documented in docs/adr/0003

    @property
    def features(self) -> list[str]:
        return list(self.metadata["features"])


def artifact_dir(models_dir: Path, task: str, name: str) -> Path:
    return Path(models_dir) / task / name


@lru_cache(maxsize=8)
def load_artifact(models_dir: Path, task: str, name: str) -> Artifact:
    """Read once per process.

    Raises:
        ArtifactNotFoundError: if the folder lacks model.txt or metadata.json.
    """
    folder = artifact_dir(models_dir, task, name)
    model, metadata = folder / "model.txt", folder / "metadata.json"
    if not model.exists() or not metadata.exists():
        raise ArtifactNotFoundError(
            f"{folder} has no model.txt/metadata.json; run notebooks/06_evaluate_and_export.ipynb"
        )
    return Artifact(
        booster=lgb.Booster(model_file=str(model)),
        metadata=json.loads(metadata.read_text(encoding="utf-8")),
    )
