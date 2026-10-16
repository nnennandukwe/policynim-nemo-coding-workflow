"""Hosted MCP client error handling tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from policynim_nemo_workflow.mcp_client import HostedPolicyMcpClient


class FakeToolResult:
    def __init__(self, structured_content: object) -> None:
        self.structuredContent = structured_content


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
