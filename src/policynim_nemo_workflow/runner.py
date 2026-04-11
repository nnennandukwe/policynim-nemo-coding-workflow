"""Workflow orchestration for baseline, policy, and compare runs."""

from __future__ import annotations

from pathlib import Path

from policynim_nemo_workflow.constraints import classify_coding_task, compile_policy_constraints
from policynim_nemo_workflow.evaluator import evaluate_artifact
from policynim_nemo_workflow.generator import generate_baseline_artifact, generate_policy_artifact
from policynim_nemo_workflow.mcp_client import PolicyClient
from policynim_nemo_workflow.models import (
    CodingTask,
    CompareResult,
    RunBundle,
    ToolCallRecord,
)
from policynim_nemo_workflow.pathing import create_run_dir, write_json_atomic


async def run_baseline(task: CodingTask, *, output_base: Path | None = None) -> RunBundle:
    """Run the generic baseline workflow."""
    artifact = generate_baseline_artifact(task)
    evaluation = evaluate_artifact(artifact)
    return _bundle(artifact, evaluation, output_base=output_base)


async def run_policy(
    task: CodingTask,
    *,
    client: PolicyClient,
    output_base: Path | None = None,
    revise_on_fail: bool = False,
) -> RunBundle:
    """Run the hosted PolicyNIM-conditioned workflow."""
    domain = task.domain or classify_coding_task(task.prompt)
    preflight = await client.policy_preflight(task=task.prompt, domain=domain, top_k=task.top_k)
    constraints = compile_policy_constraints(preflight)
    artifact = generate_policy_artifact(task, constraints)
    artifact.policy_trace.insert(
        0,
        ToolCallRecord(
            name="policy_preflight",
            arguments={"domain": domain, "top_k": task.top_k},
        ),
    )
    evaluation = evaluate_artifact(artifact)

    if revise_on_fail and not evaluation.passed:
        artifact = generate_policy_artifact(
            task,
            constraints,
            revision_count=artifact.revision_count + 1,
        )
        artifact.policy_trace.insert(
            0,
            ToolCallRecord(
                name="policy_preflight",
                arguments={"domain": domain, "top_k": task.top_k, "revision": True},
            ),
        )
        evaluation = evaluate_artifact(artifact)

    return _bundle(artifact, evaluation, output_base=output_base)


async def compare_runs(
    task: CodingTask,
    *,
    client: PolicyClient,
    output_base: Path | None = None,
    revise_on_fail: bool = False,
) -> CompareResult:
    """Run baseline and policy workflows and compare their scores."""
    baseline = await run_baseline(task, output_base=output_base)
    policy = await run_policy(
        task,
        client=client,
        output_base=output_base,
        revise_on_fail=revise_on_fail,
    )
    return CompareResult(
        baseline=baseline,
        policy=policy,
        improved=policy.evaluation.score > baseline.evaluation.score,
    )


def _bundle(artifact, evaluation, *, output_base: Path | None) -> RunBundle:  # noqa: ANN001
    output_dir: Path | None = None
    if output_base is not None:
        output_dir = create_run_dir(output_base, task_id=artifact.task_id, mode=artifact.mode)
        write_json_atomic(output_dir / "artifact.json", artifact)
        write_json_atomic(output_dir / "evaluation.json", evaluation)
    return RunBundle(artifact=artifact, evaluation=evaluation, output_dir=output_dir)
