"""Task loading and CLI behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from policynim_nemo_workflow.cli import app
from policynim_nemo_workflow.tasks import load_task


def test_load_task_validates_the_golden_scenario() -> None:
    task = load_task(Path("scenarios/refresh_token_cleanup.json"))

    assert task.task_id == "refresh-token-cleanup"
    assert task.domain == "security"


def test_load_task_reports_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(RuntimeError, match="not valid JSON"):
        load_task(path)


def test_baseline_cli_writes_artifacts_without_hosted_env(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--mode",
            "baseline",
            "--task",
            "scenarios/refresh_token_cleanup.json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "mode=baseline" in result.output
    assert list(tmp_path.glob("*/artifact.json"))
    assert list(tmp_path.glob("*/evaluation.json"))


def test_policy_cli_fails_fast_without_hosted_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POLICYNIM_BETA_MCP_URL", raising=False)
    monkeypatch.delenv("POLICYNIM_BETA_MCP_TOKEN", raising=False)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--mode",
            "policy",
            "--task",
            "scenarios/refresh_token_cleanup.json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "Hosted PolicyNIM MCP settings are missing" in result.output


def test_golden_task_json_stays_minimal_and_public() -> None:
    payload = json.loads(Path("scenarios/refresh_token_cleanup.json").read_text(encoding="utf-8"))

    assert set(payload) == {"task_id", "title", "prompt", "domain", "top_k"}
