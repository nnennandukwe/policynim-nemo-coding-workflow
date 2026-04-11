"""Compile PolicyNIM guidance into prompt-level constraints."""

from __future__ import annotations

from policynim_nemo_workflow.models import (
    PolicyConstraint,
    PolicyConstraints,
    PolicyPreflightResult,
)


def classify_coding_task(prompt: str) -> str:
    """Classify the narrow demo task into a PolicyNIM domain."""
    lowered = prompt.lower()
    if "token" in lowered or "auth" in lowered or "session" in lowered:
        return "security"
    return "backend"


def compile_policy_constraints(preflight_result: PolicyPreflightResult) -> PolicyConstraints:
    """Turn PolicyNIM preflight output into compact generation constraints."""
    if preflight_result.insufficient_context:
        return PolicyConstraints(
            summary="PolicyNIM reported insufficient context; generation must stop.",
            insufficient_context=True,
            prompt_block="PolicyNIM returned insufficient_context=true. Do not generate code.",
        )

    constraints: list[PolicyConstraint] = []
    for item in preflight_result.implementation_guidance:
        constraints.append(
            PolicyConstraint(
                kind="must",
                text=item,
                citation_ids=_all_citation_ids(preflight_result),
            )
        )
    for item in preflight_result.review_flags:
        constraints.append(
            PolicyConstraint(
                kind="avoid",
                text=item,
                citation_ids=_all_citation_ids(preflight_result),
            )
        )
    for item in preflight_result.tests_required:
        constraints.append(
            PolicyConstraint(
                kind="test",
                text=item,
                citation_ids=_all_citation_ids(preflight_result),
            )
        )

    if not constraints:
        constraints.append(
            PolicyConstraint(
                kind="must",
                text=preflight_result.summary,
                citation_ids=_all_citation_ids(preflight_result),
            )
        )

    lines = ["Policy constraints from PolicyNIM:"]
    for constraint in constraints:
        citations = ", ".join(constraint.citation_ids) or "uncited"
        lines.append(f"- {constraint.kind.upper()}: {constraint.text} [{citations}]")

    return PolicyConstraints(
        summary=preflight_result.summary,
        constraints=constraints,
        citations=preflight_result.citations,
        prompt_block="\n".join(lines),
    )


def _all_citation_ids(preflight_result: PolicyPreflightResult) -> list[str]:
    return [citation.chunk_id for citation in preflight_result.citations]
