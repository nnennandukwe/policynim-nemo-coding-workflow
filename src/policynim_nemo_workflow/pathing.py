"""Artifact path helpers with explicit normalization."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel

_SAFE_SLUG = re.compile(r"[^A-Za-z0-9_.-]+")


def slugify(value: str) -> str:
    """Return a filesystem-safe slug from a user-visible label."""
    normalized = _SAFE_SLUG.sub("-", value.strip()).strip(".-").lower()
    if not normalized:
        raise ValueError("Artifact name must contain at least one safe character.")
    return normalized[:80]


def create_run_dir(base_dir: Path, *, task_id: str, mode: str) -> Path:
    """Create a unique artifact directory for one run."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base_dir / f"{timestamp}-{slugify(task_id)}-{slugify(mode)}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json_atomic(path: Path, payload: BaseModel | dict[str, object]) -> None:
    """Write one JSON artifact atomically after the parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json")
    else:
        data = payload
    content = json.dumps(data, indent=2, sort_keys=True) + "\n"
    tmp_path: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(content)
        tmp_path.replace(path)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise
