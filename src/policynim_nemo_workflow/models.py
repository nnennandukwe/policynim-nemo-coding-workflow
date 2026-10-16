"""Typed contracts for the hosted PolicyNIM + NeMo demo."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RunMode = Literal["baseline", "policy"]
PolicyToolName = Literal["policy_preflight", "policy_search"]


class StrictModel(BaseModel):
    """Base model for explicit demo contracts."""

    model_config = ConfigDict(extra="forbid")


class CodingTask(StrictModel):
    """One coding task used by the demo."""

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    domain: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class PolicyCitation(StrictModel):
    """Citation returned by PolicyNIM."""

    policy_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    path: str = Field(min_length=1)
    section: str = Field(min_length=1)
    lines: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)


class PolicyGuidance(StrictModel):
    """One PolicyNIM guidance item."""

    policy_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    citation_ids: list[str] = Field(default_factory=list)


class PolicyPreflightResult(StrictModel):
    """Subset of PolicyNIM PreflightResult used by this demo."""

    generation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    task: str = Field(min_length=1)
    domain: str | None = None
    summary: str = Field(min_length=1)
    applicable_policies: list[PolicyGuidance] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    implementation_guidance: list[str] = Field(default_factory=list)
    review_flags: list[str] = Field(default_factory=list)
    tests_required: list[str] = Field(default_factory=list)
    citations: list[PolicyCitation] = Field(default_factory=list)
    insufficient_context: bool = False


class PolicyConstraint(StrictModel):
    """A compact constraint compiled from PolicyNIM evidence."""

    kind: Literal["must", "avoid", "test"]
    text: str = Field(min_length=1)
    citation_ids: list[str] = Field(default_factory=list)


class PolicyConstraints(StrictModel):
    """Compiled constraints that materially shape generation."""

    summary: str = Field(min_length=1)
    plan_steps: list[str] = Field(default_factory=list)
    constraints: list[PolicyConstraint] = Field(default_factory=list)
    citations: list[PolicyCitation] = Field(default_factory=list)
    prompt_block: str = Field(min_length=1)
    insufficient_context: bool = False


class ToolCallRecord(StrictModel):
    """One visible tool call in the workflow trace."""

    name: str = Field(min_length=1)
    arguments: dict[str, object] = Field(default_factory=dict)
    ok: bool = True


class GeneratedFile(StrictModel):
    """One generated file artifact."""

    path: str = Field(min_length=1)
    content: str = Field(min_length=1)


class CodingArtifact(StrictModel):
    """Plan/code/tests output from one demo run."""

    task_id: str = Field(min_length=1)
    mode: RunMode
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    plan: list[str] = Field(default_factory=list)
    unverified_plan_steps: list[str] = Field(default_factory=list)
    files: list[GeneratedFile] = Field(default_factory=list)
    tests: list[GeneratedFile] = Field(default_factory=list)
    policy_trace: list[ToolCallRecord] = Field(default_factory=list)
    citations: list[PolicyCitation] = Field(default_factory=list)
    revision_count: int = 0


class EvaluationCheck(StrictModel):
    """One deterministic policy conformance check."""

    name: str = Field(min_length=1)
    passed: bool
    message: str = Field(min_length=1)


class EvaluationResult(StrictModel):
    """Deterministic evaluation output for one artifact."""

    task_id: str = Field(min_length=1)
    mode: RunMode
    score: float = Field(ge=0.0, le=1.0)
    checks: list[EvaluationCheck] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return whether all checks passed."""
        return all(check.passed for check in self.checks)


class RunBundle(StrictModel):
    """One run plus its evaluation."""

    artifact: CodingArtifact
    evaluation: EvaluationResult
    output_dir: Path | None = None


class CompareResult(StrictModel):
    """Baseline/policy comparison result."""

    baseline: RunBundle
    policy: RunBundle
    improved: bool
