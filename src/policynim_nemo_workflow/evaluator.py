"""Deterministic policy conformance evaluator."""

from __future__ import annotations

from policynim_nemo_workflow.models import CodingArtifact, EvaluationCheck, EvaluationResult


def evaluate_artifact(artifact: CodingArtifact) -> EvaluationResult:
    """Evaluate one generated artifact against the golden policy expectations."""
    code = "\n".join(file.content for file in artifact.files)
    tests = "\n".join(file.content for file in artifact.tests)
    plan = "\n".join(artifact.plan).lower()
    trace_names = [call.name for call in artifact.policy_trace]

    checks = [
        EvaluationCheck(
            name="policy_preflight_called",
            passed=artifact.mode == "baseline" or "policy_preflight" in trace_names,
            message="Policy run must call hosted PolicyNIM policy_preflight before generation.",
        ),
        EvaluationCheck(
            name="citations_compiled",
            passed=artifact.mode == "baseline" or bool(artifact.citations),
            message="Policy run must carry PolicyNIM citations into the final artifact.",
        ),
        EvaluationCheck(
            name="active_tokens_preserved",
            passed="active" in plan and "test_cleanup_preserves_active_refresh_tokens" in tests,
            message="Artifact must preserve active refresh-token semantics and test it.",
        ),
        EvaluationCheck(
            name="raw_tokens_redacted",
            passed="token.value" not in code and "secret-token" not in code,
            message="Generated code must not log raw token values.",
        ),
        EvaluationCheck(
            name="structured_logging",
            passed="logger.info(" in code and "extra=" in code,
            message="Generated code must use structured logging metadata.",
        ),
        EvaluationCheck(
            name="service_boundary",
            passed="repo." in code and "select " not in code.lower(),
            message="Generated code must use the repository boundary instead of direct SQL.",
        ),
    ]
    if artifact.unverified_plan_steps:
        checks.append(
            EvaluationCheck(
                name="required_plan_steps_verified",
                passed=False,
                message="Requested PolicyNIM plan steps haven't been independently verified "
                "by the fixed demo generator.",
            )
        )
    if artifact.source_references:
        checks.append(
            EvaluationCheck(
                name="source_applicability_review",
                passed=False,
                message="Whole policy quotations need applicability and condition review; "
                "the fixed demo generator hasn't verified that review.",
            )
        )
    passed_count = sum(1 for check in checks if check.passed)
    return EvaluationResult(
        task_id=artifact.task_id,
        mode=artifact.mode,
        score=passed_count / len(checks),
        checks=checks,
    )


def failure_messages(result: EvaluationResult) -> list[str]:
    """Return evaluator messages for failed checks."""
    return [check.message for check in result.checks if not check.passed]
