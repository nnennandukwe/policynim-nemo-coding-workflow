"""Source quotation semantics through the public companion workflow."""

import pytest

from policynim_nemo_workflow.constraints import compile_policy_constraints
from policynim_nemo_workflow.evaluator import evaluate_artifact
from policynim_nemo_workflow.generator import generate_policy_artifact
from policynim_nemo_workflow.models import CodingTask, PolicyPreflightResult

SOURCE_BODY = (
    "# Conditional token lifecycle\n\n## Private conditions\n"
    "Rotate the session token after authentication.\n\n## Exceptions\n"
    "Don't rotate session tokens during periodic cleanup.\n\n## Violating example\n"
    "Rotating every token during cleanup violates this policy."
)


def source_preflight() -> PolicyPreflightResult:
    """Supply the producer's fixed extractive markers and a full conditional body."""
    return PolicyPreflightResult.model_validate(
        {
            "task": "Review refresh cleanup",
            "summary": (
                "Selected policy sources are quoted in full. "
                "Review their applicability to the task."
            ),
            "plan_steps": [SOURCE_BODY],
            "applicable_policies": [
                {
                    "policy_id": "SESSION-1",
                    "title": "Conditional token lifecycle",
                    "rationale": "Selected source policy; its full text appears in the plan steps.",
                    "citation_ids": ["SESSION-1:full"],
                }
            ],
            "citations": [
                {
                    "policy_id": "SESSION-1",
                    "title": "Conditional token lifecycle",
                    "path": "policies/session.md",
                    "section": "Conditional token lifecycle",
                    "lines": "1-12",
                    "chunk_id": "SESSION-1:full",
                }
            ],
        }
    )


def test_full_source_is_a_reference_without_becoming_a_mandatory_plan() -> None:
    """Conditions and violating examples mustn't become unconditional implementation steps."""
    result = compile_policy_constraints(source_preflight())
    assert all(constraint.text != SOURCE_BODY for constraint in result.constraints)
    assert [reference.body for reference in result.source_references] == [SOURCE_BODY]
    assert result.plan_steps == []
    assert "SOURCE REFERENCE" in result.prompt_block
    assert SOURCE_BODY in result.prompt_block
    artifact = generate_policy_artifact(
        CodingTask(task_id="cleanup", title="Cleanup", prompt="Review refresh cleanup"), result
    )
    assert artifact.source_references == result.source_references
    assert SOURCE_BODY not in artifact.plan
    evaluation = evaluate_artifact(artifact)
    check = next(c for c in evaluation.checks if c.name == "source_applicability_review")
    assert not check.passed
    assert not evaluation.passed


@pytest.mark.parametrize(
    "mutation",
    ["summary", "rationale", "advice", "missing_body", "missing_reference", "wrong_owner"],
)
def test_malformed_extractive_contract_stops_before_generation(mutation: str) -> None:
    """Recognized source markers can't fall back to stronger historical must semantics."""
    result = source_preflight()
    if mutation == "summary":
        result.summary = "Changed summary"
    elif mutation == "rationale":
        result.applicable_policies[0].rationale = "Changed rationale"
    elif mutation == "advice":
        result.implementation_guidance = ["Rotate on every cleanup batch."]
    elif mutation == "missing_body":
        result.plan_steps = []
    elif mutation == "missing_reference":
        result.citations = []
    elif mutation == "wrong_owner":
        result.citations[0].policy_id = "OTHER"
    with pytest.raises(ValueError, match="source-reference envelope isn't valid"):
        compile_policy_constraints(result)


def test_legacy_response_and_artifact_keep_backward_default_reference_fields() -> None:
    """Historical synthesized plan steps retain their existing compilation and load behavior."""
    from policynim_nemo_workflow.models import CodingArtifact, PolicyConstraints

    preflight = source_preflight()
    preflight.summary = "A historical synthesized plan"
    preflight.applicable_policies[0].rationale = "Historical selected guidance"
    preflight.plan_steps = ["Preserve active sessions."]
    result = compile_policy_constraints(preflight)
    assert result.source_references == []
    assert result.plan_steps == preflight.plan_steps
    assert result.constraints[0].kind == "must"
    assert result.constraints[0].text == "Preserve active sessions."
    old_constraints = result.model_dump(exclude={"source_references"})
    assert PolicyConstraints.model_validate(old_constraints).source_references == []
    assert (
        CodingArtifact.model_validate(
            {"task_id": "historical", "mode": "policy", "plan": ["Existing plan"]}
        ).source_references
        == []
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("identical_bodies", [False, True])
async def test_saved_multi_policy_run_keeps_each_source_owner_and_references(
    tmp_path, identical_bodies: bool
) -> None:
    """The persisted public workflow retains owner identity even for identical bodies."""
    import json

    from policynim_nemo_workflow.models import CodingArtifact
    from policynim_nemo_workflow.runner import run_policy

    result = source_preflight()
    other_body = SOURCE_BODY if identical_bodies else "# Different policy\nKeep its conditions."
    result.plan_steps.append(other_body)
    result.applicable_policies.append(
        result.applicable_policies[0].model_copy(
            update={"policy_id": "OTHER", "title": "Other policy", "citation_ids": ["OTHER:full"]}
        )
    )
    result.citations.append(
        result.citations[0].model_copy(
            update={"policy_id": "OTHER", "title": "Other policy", "chunk_id": "OTHER:full"}
        )
    )

    class SuppliedPreflightClient:
        """Return the reviewed source envelope without an external request."""

        async def policy_preflight(self, *, task, domain, top_k):
            """Expose the ordinary workflow's typed preflight boundary."""
            return result

    bundle = await run_policy(
        CodingTask(task_id="cleanup", title="Cleanup", prompt="Review refresh cleanup"),
        client=SuppliedPreflightClient(),
        output_base=tmp_path,
        revise_on_fail=True,
    )
    assert bundle.output_dir is not None
    raw = json.loads((bundle.output_dir / "artifact.json").read_text())
    assert raw["source_references"] == [
        {
            "policy_id": "SESSION-1",
            "title": "Conditional token lifecycle",
            "body": SOURCE_BODY,
            "citation_ids": ["SESSION-1:full"],
        },
        {
            "policy_id": "OTHER",
            "title": "Other policy",
            "body": other_body,
            "citation_ids": ["OTHER:full"],
        },
    ]
    assert CodingArtifact.model_validate(raw).source_references == bundle.artifact.source_references
    assert not bundle.evaluation.passed
    assert bundle.artifact.revision_count == 1


def test_extractive_response_retains_global_citation_without_claiming_an_owner() -> None:
    """A top-level compiler reference needn't be assigned to a quoted policy body."""
    result = source_preflight()
    extra = result.citations[0].model_copy(
        update={"policy_id": "GLOBAL", "title": "Compiler reference", "chunk_id": "GLOBAL:rule"}
    )
    result.citations.append(extra)
    compiled = compile_policy_constraints(result)
    assert compiled.citations == result.citations
    assert compiled.source_references[0].citation_ids == ["SESSION-1:full"]
