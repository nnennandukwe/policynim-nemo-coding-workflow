"""NeMo Agent Toolkit component registration for demo-local tools."""

from __future__ import annotations

from collections.abc import AsyncIterator

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig
from pydantic import BaseModel, Field

from policynim_nemo_workflow.constraints import classify_coding_task


class TaskTextInput(BaseModel):
    """Generic text input for demo-local NAT tools."""

    text: str = Field(description="Task, policy, or evaluator text.")


class DemoTextOutput(BaseModel):
    """Generic text output for demo-local NAT tools."""

    text: str


class ClassifyCodingTaskConfig(FunctionBaseConfig, name="classify_coding_task"):
    """Classify the coding task into a policy domain."""


class CompilePolicyConstraintsConfig(FunctionBaseConfig, name="compile_policy_constraints"):
    """Compile PolicyNIM output into concise generation constraints."""


class EmitCodingArtifactConfig(FunctionBaseConfig, name="emit_coding_artifact"):
    """Emit the final coding artifact."""


class ReviseFailedArtifactConfig(FunctionBaseConfig, name="revise_failed_artifact"):
    """Revise the coding artifact when evaluation fails."""


@register_function(config_type=ClassifyCodingTaskConfig)
async def register_classify_coding_task(
    config: ClassifyCodingTaskConfig,  # noqa: ARG001
    builder: Builder,  # noqa: ARG001
) -> AsyncIterator[FunctionInfo]:
    """Register the task classifier tool."""

    async def _classify(message: TaskTextInput) -> DemoTextOutput:
        return DemoTextOutput(text=classify_coding_task(message.text))

    yield FunctionInfo.from_fn(
        _classify,
        description="Classify a coding task into a PolicyNIM retrieval domain.",
    )


@register_function(config_type=CompilePolicyConstraintsConfig)
async def register_compile_policy_constraints(
    config: CompilePolicyConstraintsConfig,  # noqa: ARG001
    builder: Builder,  # noqa: ARG001
) -> AsyncIterator[FunctionInfo]:
    """Register the policy constraint compiler tool."""

    async def _compile(message: TaskTextInput) -> DemoTextOutput:
        return DemoTextOutput(
            text=(
                "Compile PolicyNIM preflight citations into must/avoid/test constraints. "
                f"Input summary: {message.text}"
            )
        )

    yield FunctionInfo.from_fn(
        _compile,
        description="Compile PolicyNIM guidance into constraints before generation.",
    )


@register_function(config_type=EmitCodingArtifactConfig)
async def register_emit_coding_artifact(
    config: EmitCodingArtifactConfig,  # noqa: ARG001
    builder: Builder,  # noqa: ARG001
) -> AsyncIterator[FunctionInfo]:
    """Register the artifact emitter tool."""

    async def _emit(message: TaskTextInput) -> DemoTextOutput:
        return DemoTextOutput(text=f"Emit coding artifact for: {message.text}")

    yield FunctionInfo.from_fn(
        _emit,
        description="Emit a structured plan/code/tests artifact.",
    )


@register_function(config_type=ReviseFailedArtifactConfig)
async def register_revise_failed_artifact(
    config: ReviseFailedArtifactConfig,  # noqa: ARG001
    builder: Builder,  # noqa: ARG001
) -> AsyncIterator[FunctionInfo]:
    """Register the revision tool."""

    async def _revise(message: TaskTextInput) -> DemoTextOutput:
        return DemoTextOutput(text=f"Revise artifact using evaluator failures: {message.text}")

    yield FunctionInfo.from_fn(
        _revise,
        description="Revise a failed artifact using evaluator failures.",
    )
