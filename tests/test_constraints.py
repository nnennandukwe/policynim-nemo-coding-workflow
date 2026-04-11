"""Behavior tests for PolicyNIM constraint compilation."""

from __future__ import annotations

from policynim_nemo_workflow.constraints import classify_coding_task, compile_policy_constraints
from policynim_nemo_workflow.models import (
    PolicyCitation,
    PolicyGuidance,
    PolicyPreflightResult,
)


def _preflight(**overrides: object) -> PolicyPreflightResult:
    payload: dict[str, object] = {
        "task": "refresh-token cleanup",
        "domain": "security",
        "summary": "Cleanup must preserve revocation semantics.",
        "applicable_policies": [
            {
                "policy_id": "AUTH-001",
                "title": "Auth Reviews",
                "rationale": "Token cleanup must preserve active sessions.",
                "citation_ids": ["AUTH-1"],
            }
        ],
        "implementation_guidance": [
            "Delete only expired tokens and preserve active-token semantics."
        ],
        "review_flags": ["Do not log raw token values."],
        "tests_required": ["Add coverage for active-token preservation."],
        "citations": [
            {
                "policy_id": "AUTH-001",
                "title": "Auth Reviews",
                "path": "policies/security/auth-sensitive-code-review-standard.md",
                "section": "Cleanup",
                "lines": "10-16",
                "chunk_id": "AUTH-1",
            }
        ],
        "insufficient_context": False,
    }
    payload.update(overrides)
    return PolicyPreflightResult.model_validate(payload)


def test_classify_coding_task_maps_token_work_to_security_domain() -> None:
    assert classify_coding_task("Implement refresh token cleanup") == "security"


def test_compile_policy_constraints_carries_citations_into_prompt_block() -> None:
    result = compile_policy_constraints(_preflight())

    assert result.insufficient_context is False
    assert result.citations == [
        PolicyCitation(
            policy_id="AUTH-001",
            title="Auth Reviews",
            path="policies/security/auth-sensitive-code-review-standard.md",
            section="Cleanup",
            lines="10-16",
            chunk_id="AUTH-1",
        )
    ]
    assert "AUTH-1" in result.prompt_block
    assert any(constraint.kind == "avoid" for constraint in result.constraints)
    assert any("raw token" in constraint.text for constraint in result.constraints)


def test_compile_policy_constraints_fails_closed_on_insufficient_context() -> None:
    result = compile_policy_constraints(
        _preflight(
            insufficient_context=True,
            applicable_policies=[PolicyGuidance(policy_id="AUTH-001", title="Auth", rationale="x")],
        )
    )

    assert result.insufficient_context is True
    assert result.constraints == []
    assert "Do not generate code" in result.prompt_block
