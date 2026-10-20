"""Hosted MCP client error handling tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult, TextContent

from policynim_nemo_workflow.mcp_client import HostedPolicyMcpClient


class FakeToolResult:
    def __init__(self, structured_content: object) -> None:
        """Model successful results independently from the actual SDK error envelope."""
        self.structuredContent = structured_content
        self.isError = False


class FakeSession:
    def __init__(self, structured_content: object) -> None:
        self._structured_content = structured_content

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> FakeToolResult:
        return FakeToolResult(self._structured_content)


def _client_with_payload(payload: object) -> HostedPolicyMcpClient:
    client = HostedPolicyMcpClient.__new__(HostedPolicyMcpClient)

    @asynccontextmanager
    async def fake_session():
        yield FakeSession(payload)

    client._session = fake_session
    return client


@pytest.mark.asyncio
async def test_policy_preflight_reports_non_dict_structured_content() -> None:
    client = _client_with_payload(["not", "a", "dict"])

    with pytest.raises(RuntimeError, match="received list"):
        await client.policy_preflight(
            task="Implement refresh-token cleanup.",
            domain="security",
            top_k=3,
        )


@pytest.mark.asyncio
async def test_policy_preflight_wraps_invalid_structured_content() -> None:
    client = _client_with_payload({"task": "Implement refresh-token cleanup."})

    with pytest.raises(RuntimeError, match="invalid structured content") as exc_info:
        await client.policy_preflight(
            task="Implement refresh-token cleanup.",
            domain="security",
            top_k=3,
        )

    assert exc_info.value.__cause__ is not None


@pytest.fixture
def producer_preflight_payload() -> dict[str, object]:
    """Load JSON serialized by PolicyNIM PreflightResult at producer revision 10d4e86."""
    import json

    path = Path(__file__).parent / "fixtures" / "policynim_preflight_generation.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_policy_preflight_accepts_generation_and_plan_steps(
    producer_preflight_payload: dict[str, object],
) -> None:
    """The real client preserves the complete producer payload, including nested citations."""
    client = _client_with_payload(producer_preflight_payload)
    result = await client.policy_preflight(
        task="Implement refresh-token cleanup.", domain="security", top_k=3
    )
    assert result.model_dump(mode="json") == producer_preflight_payload


@pytest.mark.asyncio
@pytest.mark.parametrize("generation", [None, "omitted"])
async def test_policy_preflight_accepts_older_payloads(
    producer_preflight_payload: dict[str, object], generation: str | None
) -> None:
    """Legacy and source-only responses keep working without a generation or plan."""
    producer_preflight_payload.pop("plan_steps")
    if generation == "omitted":
        producer_preflight_payload.pop("generation_id")
    else:
        producer_preflight_payload["generation_id"] = generation
    result = await _client_with_payload(producer_preflight_payload).policy_preflight(
        task="Implement refresh-token cleanup.", domain="security", top_k=3
    )
    assert result.generation_id is None
    assert result.plan_steps == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"unexpected_field": True},
        {"generation_id": "not-a-generation"},
        {"generation_id": "A" * 64},
        {"generation_id": "a" * 63},
        {"plan_steps": "check expiry"},
        {"plan_steps": [123]},
    ],
)
async def test_policy_preflight_still_rejects_invalid_payloads(
    producer_preflight_payload: dict[str, object], changes: dict[str, object]
) -> None:
    """Known optional fields don't weaken unknown-field, ID or plan-item validation."""
    producer_preflight_payload.update(changes)
    with pytest.raises(RuntimeError, match="invalid structured content") as error:
        await _client_with_payload(producer_preflight_payload).policy_preflight(
            task="Implement refresh-token cleanup.", domain="security", top_k=3
        )
    assert error.value.__cause__ is not None


def test_preflight_plan_steps_reach_compiled_constraints(
    producer_preflight_payload: dict[str, object],
) -> None:
    """Producer-required plan steps stay visible in the generation constraints."""
    from policynim_nemo_workflow.constraints import compile_policy_constraints
    from policynim_nemo_workflow.models import PolicyPreflightResult

    preflight = PolicyPreflightResult.model_validate(producer_preflight_payload)
    constraints = compile_policy_constraints(preflight)
    for step in preflight.plan_steps:
        assert step in constraints.prompt_block
        assert any(item.kind == "must" and item.text == step for item in constraints.constraints)


@pytest.mark.asyncio
async def test_preflight_plan_steps_survive_the_saved_workflow_artifact(
    producer_preflight_payload: dict[str, object], tmp_path: Path
) -> None:
    """A real client-to-runner execution retains the producer's ordered required steps on disk."""
    import json

    from policynim_nemo_workflow.models import CodingTask, PolicyPreflightResult
    from policynim_nemo_workflow.runner import run_policy

    task = CodingTask(
        task_id="token-cleanup", title="Token cleanup", prompt="Implement refresh-token cleanup."
    )
    preflight = PolicyPreflightResult.model_validate(producer_preflight_payload)
    bundle = await run_policy(
        task, client=_client_with_payload(producer_preflight_payload), output_base=tmp_path
    )
    assert bundle.artifact.plan[: len(preflight.plan_steps)] == preflight.plan_steps
    assert bundle.artifact.citations == preflight.citations
    assert bundle.output_dir is not None
    saved = json.loads((bundle.output_dir / "artifact.json").read_text())
    assert saved["plan"] == bundle.artifact.plan


@pytest.mark.asyncio
@pytest.mark.parametrize("steps", [[""], ["  ", "Check revocation before deleting.", ""]])
async def test_blank_preflight_steps_dont_stop_the_policy_workflow(
    producer_preflight_payload: dict[str, object], steps: list[str], tmp_path: Path
) -> None:
    """Producer-valid blank entries can't abort compilation or leak into the saved plan."""
    from policynim_nemo_workflow.models import CodingTask
    from policynim_nemo_workflow.runner import run_policy

    producer_preflight_payload["plan_steps"] = steps
    task = CodingTask(task_id="cleanup", title="Cleanup", prompt="Implement token cleanup.")
    bundle = await run_policy(
        task, client=_client_with_payload(producer_preflight_payload), output_base=tmp_path
    )
    meaningful = [step for step in steps if step.strip()]
    assert bundle.artifact.plan[: len(meaningful)] == meaningful
    assert all(step.strip() for step in bundle.artifact.plan)
    assert bundle.output_dir is not None
    assert (bundle.output_dir / "artifact.json").is_file()


@pytest.mark.asyncio
async def test_requested_plan_isnt_reported_as_verified_code(
    producer_preflight_payload: dict[str, object], tmp_path: Path
) -> None:
    """Keep requested steps unverified through generation, retry and saved evaluation."""
    import json

    from policynim_nemo_workflow.models import CodingTask, PolicyPreflightResult
    from policynim_nemo_workflow.runner import run_policy

    task = CodingTask(task_id="cleanup", title="Cleanup", prompt="Implement token cleanup.")
    preflight = PolicyPreflightResult.model_validate(producer_preflight_payload)
    bundle = await run_policy(
        task,
        client=_client_with_payload(producer_preflight_payload),
        output_base=tmp_path,
        revise_on_fail=True,
    )
    assert bundle.evaluation.passed is False
    assert bundle.artifact.revision_count == 1
    assert bundle.artifact.unverified_plan_steps == preflight.plan_steps
    failed = [check for check in bundle.evaluation.checks if not check.passed]
    assert any(check.name == "required_plan_steps_verified" for check in failed)
    assert bundle.output_dir is not None
    artifact = json.loads((bundle.output_dir / "artifact.json").read_text())
    evaluation = json.loads((bundle.output_dir / "evaluation.json").read_text())
    assert artifact["unverified_plan_steps"] == preflight.plan_steps
    assert any(
        check["name"] == "required_plan_steps_verified" and not check["passed"]
        for check in evaluation["checks"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "quota_exceeded: Daily allowance reached. Retry after 2026-10-21T00:00:00Z.",
        "admission_busy: Capacity is occupied. Retry in one second.",
    ],
)
async def test_tool_error_preserves_recovery_before_success_validation(message: str) -> None:
    """Actual SDK errors must retain the server's quota and retry instructions."""
    client = HostedPolicyMcpClient.__new__(HostedPolicyMcpClient)
    client._token = "private-token"
    result = CallToolResult(
        isError=True,
        structuredContent={"task": "untrusted success-shaped data"},
        content=[TextContent(type="text", text=message)],
    )

    @asynccontextmanager
    async def error_session():
        """Deliver the real SDK envelope through the public client operation."""
        yield SimpleNamespace(call_tool=AsyncMock(return_value=result))

    client._session = error_session
    with pytest.raises(RuntimeError) as error:
        await client.policy_preflight(task="Implement cleanup.", domain="security", top_k=3)
    assert message in str(error.value)
    assert "invalid structured content" not in str(error.value)


@pytest.mark.asyncio
async def test_tool_error_redacts_credentials_and_bounds_remote_text() -> None:
    """Remote text can't expose the bearer credential or produce unbounded output."""
    client = HostedPolicyMcpClient.__new__(HostedPolicyMcpClient)
    client._token = "private-bearer-token"
    result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text=client._token + " " + "x" * 10000)],
    )

    @asynccontextmanager
    async def error_session():
        """Keep transport behavior identical to the other error-envelope witnesses."""
        yield SimpleNamespace(call_tool=AsyncMock(return_value=result))

    client._session = error_session
    with pytest.raises(RuntimeError) as error:
        await client.policy_preflight(task="Implement cleanup.", domain=None, top_k=3)
    assert client._token not in str(error.value)
    assert "<redacted>" in str(error.value)
    assert len(str(error.value)) < 2100
