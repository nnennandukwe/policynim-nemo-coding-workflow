"""Workflow invariant tests for baseline, policy, and compare runs."""

from __future__ import annotations

import pytest

from policynim_nemo_workflow.models import CodingTask, PolicyPreflightResult
from policynim_nemo_workflow.runner import compare_runs, run_policy


class FakePolicyClient:
    def __init__(self, *, insufficient_context: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self.insufficient_context = insufficient_context

    async def list_tools(self) -> list[str]:
        return ["policy_preflight", "policy_search"]

    async def policy_preflight(
        self,
        *,
        task: str,
        domain: str | None,
        top_k: int,
    ) -> PolicyPreflightResult:
        self.calls.append({"task": task, "domain": domain, "top_k": top_k})
        return PolicyPreflightResult.model_validate(
            {
                "task": task,
                "domain": domain,
                "summary": "Use policy guidance.",
                "implementation_guidance": ["Preserve active refresh-token semantics."],
                "review_flags": ["Do not log raw token values."],
                "tests_required": ["Add active-token preservation coverage."],
                "citations": [
                    {
                        "policy_id": "AUTH-001",
                        "title": "Auth Reviews",
                        "path": "policies/security/auth.md",
                        "section": "Cleanup",
                        "lines": "10-16",
                        "chunk_id": "AUTH-1",
                    }
                ],
                "insufficient_context": self.insufficient_context,
            }
        )


def _task() -> CodingTask:
    return CodingTask(
        task_id="refresh-token-cleanup",
        title="Refresh token cleanup",
        prompt="Implement refresh token cleanup.",
        domain="security",
        top_k=3,
    )


@pytest.mark.asyncio
async def test_policy_run_calls_preflight_before_evaluation() -> None:
    client = FakePolicyClient()

    bundle = await run_policy(_task(), client=client)

    assert client.calls == [
        {"task": "Implement refresh token cleanup.", "domain": "security", "top_k": 3}
    ]
    assert bundle.evaluation.passed is True
    assert bundle.artifact.policy_trace[0].name == "policy_preflight"


@pytest.mark.asyncio
async def test_compare_requires_policy_score_to_beat_baseline() -> None:
    result = await compare_runs(_task(), client=FakePolicyClient())

    assert result.improved is True
    assert result.policy.evaluation.score > result.baseline.evaluation.score


@pytest.mark.asyncio
async def test_policy_run_refuses_to_generate_when_preflight_has_insufficient_context() -> None:
    with pytest.raises(RuntimeError, match="insufficient context"):
        await run_policy(_task(), client=FakePolicyClient(insufficient_context=True))
