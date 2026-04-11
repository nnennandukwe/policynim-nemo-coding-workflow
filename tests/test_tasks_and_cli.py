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


def test_load_task_reports_invalid_schema_with_path(tmp_path: Path) -> None:
    path = tmp_path / "bad-schema.json"
    path.write_text(json.dumps({"task_id": "refresh-token-cleanup"}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid schema") as exc_info:
        load_task(path)

    assert str(path) in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


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


def test_inspect_mcp_cli_reports_tool_listing_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingClient:
        def __init__(self, settings: object) -> None:
            pass

        async def list_tools(self) -> list[str]:
            raise RuntimeError("tool listing unavailable")

    monkeypatch.setattr("policynim_nemo_workflow.cli.HostedPolicyMcpClient", FailingClient)

    result = CliRunner().invoke(app, ["inspect-mcp"])

    assert result.exit_code != 0
    assert "Hosted MCP inspection failed: tool listing unavailable" in result.output


def test_policy_cli_reports_workflow_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubClient:
        def __init__(self, settings: object) -> None:
            pass

    async def fail_run_policy(*args: object, **kwargs: object) -> object:
        raise RuntimeError("hosted preflight unavailable")

    monkeypatch.setattr("policynim_nemo_workflow.cli.HostedPolicyMcpClient", StubClient)
    monkeypatch.setattr("policynim_nemo_workflow.cli.run_policy", fail_run_policy)

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
    assert "Policy workflow failed: hosted preflight unavailable" in result.output


def test_compare_cli_reports_workflow_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubClient:
        def __init__(self, settings: object) -> None:
            pass

    async def fail_compare_runs(*args: object, **kwargs: object) -> object:
        raise RuntimeError("comparison unavailable")

    monkeypatch.setattr("policynim_nemo_workflow.cli.HostedPolicyMcpClient", StubClient)
    monkeypatch.setattr("policynim_nemo_workflow.cli.compare_runs", fail_compare_runs)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--mode",
            "compare",
            "--task",
            "scenarios/refresh_token_cleanup.json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "Comparison workflow failed: comparison unavailable" in result.output


def test_golden_task_json_stays_minimal_and_public() -> None:
    payload = json.loads(Path("scenarios/refresh_token_cleanup.json").read_text(encoding="utf-8"))

    assert set(payload) == {"task_id", "title", "prompt", "domain", "top_k"}
