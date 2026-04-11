"""Settings parity and runtime path-safety tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from policynim_nemo_workflow.models import EvaluationCheck, EvaluationResult
from policynim_nemo_workflow.pathing import create_run_dir, slugify, write_json_atomic
from policynim_nemo_workflow.settings import DemoSettings


def test_demo_settings_treat_blank_env_vars_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLICYNIM_BETA_MCP_URL", " ")
    monkeypatch.setenv("POLICYNIM_BETA_MCP_TOKEN", "")

    settings = DemoSettings()

    with pytest.raises(RuntimeError, match="POLICYNIM_BETA_MCP_URL, POLICYNIM_BETA_MCP_TOKEN"):
        settings.require_hosted_mcp()


def test_demo_settings_accept_hosted_mcp_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLICYNIM_BETA_MCP_URL", "https://example.com/mcp")
    monkeypatch.setenv("POLICYNIM_BETA_MCP_TOKEN", "token")

    DemoSettings().require_hosted_mcp()


def test_slugify_rejects_empty_or_separator_only_names() -> None:
    with pytest.raises(ValueError, match="safe character"):
        slugify("../")


def test_create_run_dir_sanitizes_task_and_mode(tmp_path: Path) -> None:
    run_dir = create_run_dir(tmp_path, task_id="../Refresh Token Cleanup", mode="policy mode")

    assert run_dir.parent == tmp_path
    assert ".." not in run_dir.name
    assert "refresh-token-cleanup" in run_dir.name
    assert "policy-mode" in run_dir.name


def test_write_json_atomic_writes_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "evaluation.json"
    result = EvaluationResult(
        task_id="refresh-token-cleanup",
        mode="policy",
        score=1.0,
        checks=[EvaluationCheck(name="ok", passed=True, message="passed")],
    )

    write_json_atomic(path, result)

    assert json.loads(path.read_text(encoding="utf-8"))["score"] == 1.0
    assert not list(tmp_path.glob("nested/tmp*"))


def test_write_json_atomic_cleans_temp_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "evaluation.json"

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        write_json_atomic(path, {"score": 1.0})

    assert not path.exists()
    assert not any(path.parent.iterdir())
