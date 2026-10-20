"""Compile PolicyNIM guidance into prompt-level constraints."""

from __future__ import annotations

from policynim_nemo_workflow.models import (
    PolicyConstraint,
    PolicyConstraints,
    PolicyPreflightResult,
    PolicySourceReference,
)

EXTRACTIVE_SUMMARY = (
    "Selected policy sources are quoted in full. Review their applicability to the task."
)
EXTRACTIVE_RATIONALE = "Selected source policy; its full text appears in the plan steps."


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

    if preflight_result.summary == EXTRACTIVE_SUMMARY or any(
        policy.rationale == EXTRACTIVE_RATIONALE for policy in preflight_result.applicable_policies
    ):
        return _compile_source_references(preflight_result)

    plan_steps = [step for step in preflight_result.plan_steps if step.strip()]
    constraints: list[PolicyConstraint] = []
    for item in [*plan_steps, *preflight_result.implementation_guidance]:
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
        plan_steps=plan_steps,
        constraints=constraints,
        citations=preflight_result.citations,
        prompt_block="\n".join(lines),
    )


def _all_citation_ids(preflight_result: PolicyPreflightResult) -> list[str]:
    """Retain ordinary historical guidance references without changing their meaning."""
    return [citation.chunk_id for citation in preflight_result.citations]


def _compile_source_references(preflight_result: PolicyPreflightResult) -> PolicyConstraints:
    """Keep the explicit extractive contract as unverified whole-source references."""
    policies = preflight_result.applicable_policies
    citations = {citation.chunk_id: citation for citation in preflight_result.citations}
    if (
        preflight_result.summary != EXTRACTIVE_SUMMARY
        or not policies
        or len(preflight_result.plan_steps) != len(policies)
        or any(not body.strip() for body in preflight_result.plan_steps)
        or any(
            (
                preflight_result.implementation_guidance,
                preflight_result.review_flags,
                preflight_result.tests_required,
            )
        )
        or len({policy.policy_id for policy in policies}) != len(policies)
        or len(citations) != len(preflight_result.citations)
        or not {citation_id for policy in policies for citation_id in policy.citation_ids}
        <= set(citations)
        or any(
            policy.rationale != EXTRACTIVE_RATIONALE
            or not policy.citation_ids
            or len(set(policy.citation_ids)) != len(policy.citation_ids)
            or any(
                citation_id not in citations
                or citations[citation_id].policy_id != policy.policy_id
                or citations[citation_id].title != policy.title
                for citation_id in policy.citation_ids
            )
            for policy in policies
        )
    ):
        raise ValueError("PolicyNIM source-reference envelope isn't valid; generation must stop.")
    lines = [
        "Unverified policy source references from PolicyNIM:",
        "Review applicability, conditions, exceptions and examples before implementation.",
        "These quotations aren't mandatory plan steps or proof of policy compliance.",
    ]
    for policy, body in zip(policies, preflight_result.plan_steps, strict=True):
        lines.append(f"SOURCE REFERENCE {policy.policy_id}: {policy.title}")
        lines.append(body)
        lines.append(f"Citations: {', '.join(policy.citation_ids)}")
    return PolicyConstraints(
        summary=preflight_result.summary,
        source_references=[
            PolicySourceReference(
                policy_id=policy.policy_id,
                title=policy.title,
                body=body,
                citation_ids=list(policy.citation_ids),
            )
            for policy, body in zip(policies, preflight_result.plan_steps, strict=True)
        ],
        citations=preflight_result.citations,
        prompt_block="\n".join(lines),
    )
