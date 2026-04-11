"""Task loading for the single golden demo scenario."""

from __future__ import annotations

import json
from pathlib import Path

from policynim_nemo_workflow.models import CodingTask


def load_task(path: Path) -> CodingTask:
    """Load and validate one coding task JSON file."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Task file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Task file is not valid JSON: {path}") from exc
    return CodingTask.model_validate(payload)
