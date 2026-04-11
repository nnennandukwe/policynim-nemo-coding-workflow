"""Behavior tests for deterministic policy conformance evaluation."""

from __future__ import annotations

from policynim_nemo_workflow.constraints import compile_policy_constraints
from policynim_nemo_workflow.evaluator import evaluate_artifact, failure_messages
from policynim_nemo_workflow.generator import generate_baseline_artifact, generate_policy_artifact
from policynim_nemo_workflow.models import CodingTask, PolicyPreflightResult, ToolCallRecord


def _task() -> CodingTask:
    return CodingTask(
        task_id="refresh-token-cleanup",
        title="Refresh token cleanup",
        prompt="Implement refresh token cleanup.",
        domain="security",
    )


def _preflight() -> PolicyPreflightResult:
    return PolicyPreflightResult.model_validate(
        {
            "task": "Implement refresh token cleanup.",
            "domain": "security",
            "summary": "Cleanup must preserve active sessions and auditability.",
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
        }
    )


def test_baseline_scores_lower_than_policy_conditioned_artifact() -> None:
    task = _task()
    baseline = generate_baseline_artifact(task)
    policy = generate_policy_artifact(task, compile_policy_constraints(_preflight()))
    policy.policy_trace.insert(0, ToolCallRecord(name="policy_preflight", arguments={}))

    baseline_result = evaluate_artifact(baseline)
    policy_result = evaluate_artifact(policy)

    assert baseline_result.score < policy_result.score
    assert policy_result.passed is True
    assert "Generated code must not log raw token values." in failure_messages(baseline_result)


def test_policy_artifact_without_preflight_tool_call_fails_trajectory_check() -> None:
    artifact = generate_policy_artifact(_task(), compile_policy_constraints(_preflight()))

    result = evaluate_artifact(artifact)

    failed = {check.name for check in result.checks if not check.passed}
    assert "policy_preflight_called" in failed
