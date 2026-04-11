"""CLI surface for the hosted PolicyNIM + NeMo demo."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from enum import StrEnum
from pathlib import Path
from typing import Annotated, TypeVar

import typer

from policynim_nemo_workflow.mcp_client import HostedPolicyMcpClient
from policynim_nemo_workflow.models import RunBundle
from policynim_nemo_workflow.runner import compare_runs, run_baseline, run_policy
from policynim_nemo_workflow.settings import DemoSettings
from policynim_nemo_workflow.tasks import load_task

app = typer.Typer(help="Hosted PolicyNIM + NVIDIA NeMo coding workflow demo.")
T = TypeVar("T")


class WorkflowMode(StrEnum):
    baseline = "baseline"
    policy = "policy"
    compare = "compare"


@app.command("inspect-mcp")
def inspect_mcp() -> None:
    """List tools exposed by the hosted PolicyNIM MCP server."""
    settings = DemoSettings()
    try:
        client = HostedPolicyMcpClient(settings)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    tools = _run_async(client.list_tools(), operation="Hosted MCP inspection")
    typer.echo("Hosted PolicyNIM MCP tools:")
    for tool in tools:
        typer.echo(f"- {tool}")


@app.command("run")
def run(
    mode: Annotated[
        WorkflowMode,
        typer.Option(help="Workflow mode to run."),
    ] = WorkflowMode.compare,
    task: Annotated[
        Path,
        typer.Option(help="Path to the demo task JSON."),
    ] = Path("scenarios/refresh_token_cleanup.json"),
    output_dir: Annotated[
        Path,
        typer.Option(help="Directory for run artifacts."),
    ] = Path("artifacts/runs"),
    revise_on_fail: Annotated[
        bool,
        typer.Option(help="Retry the policy workflow once if evaluation fails."),
    ] = True,
) -> None:
    """Run the baseline, policy, or comparison workflow."""
    coding_task = load_task(task)
    output_dir.mkdir(parents=True, exist_ok=True)

    if mode is WorkflowMode.baseline:
        bundle = _run_async(
            run_baseline(coding_task, output_base=output_dir),
            operation="Baseline workflow",
        )
        _print_bundle(bundle)
        return

    settings = DemoSettings()
    try:
        client = HostedPolicyMcpClient(settings)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if mode is WorkflowMode.policy:
        bundle = _run_async(
            run_policy(
                coding_task,
                client=client,
                output_base=output_dir,
                revise_on_fail=revise_on_fail,
            ),
            operation="Policy workflow",
        )
        _print_bundle(bundle)
        return

    if mode is WorkflowMode.compare:
        result = _run_async(
            compare_runs(
                coding_task,
                client=client,
                output_base=output_dir,
                revise_on_fail=revise_on_fail,
            ),
            operation="Comparison workflow",
        )
        typer.echo(
            f"baseline={result.baseline.evaluation.score:.2f} "
            f"policy={result.policy.evaluation.score:.2f} improved={result.improved}"
        )
        typer.echo(f"baseline_artifacts={result.baseline.output_dir}")
        typer.echo(f"policy_artifacts={result.policy.output_dir}")
        raise typer.Exit(0 if result.improved else 1)


def _print_bundle(bundle: RunBundle) -> None:
    typer.echo(f"mode={bundle.artifact.mode} score={bundle.evaluation.score:.2f}")
    if bundle.output_dir is not None:
        typer.echo(f"artifacts={bundle.output_dir}")


def _run_async(coro: Awaitable[T], *, operation: str) -> T:
    try:
        return asyncio.run(coro)
    except Exception as exc:
        typer.echo(f"{operation} failed: {exc}", err=True)
        raise typer.Exit(1) from exc
