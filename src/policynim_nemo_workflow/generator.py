"""Small deterministic generator used for reproducible demo artifacts."""

from __future__ import annotations

from policynim_nemo_workflow.models import (
    CodingArtifact,
    CodingTask,
    GeneratedFile,
    PolicyConstraints,
    ToolCallRecord,
)


def generate_baseline_artifact(task: CodingTask) -> CodingArtifact:
    """Generate the intentionally generic baseline artifact."""
    return CodingArtifact(
        task_id=task.task_id,
        mode="baseline",
        plan=[
            "Find expired refresh tokens.",
            "Delete matching records.",
            "Add a basic cleanup test.",
        ],
        files=[
            GeneratedFile(
                path="demo_app/token_cleanup.py",
                content="""def cleanup_refresh_tokens(repo, logger, now):
    expired_tokens = repo.find_expired(now)
    for token in expired_tokens:
        logger.info(f"deleting refresh token {token.value}")
        repo.delete(token.id)
    return len(expired_tokens)
""",
            )
        ],
        tests=[
            GeneratedFile(
                path="tests/test_token_cleanup.py",
                content="""def test_cleanup_deletes_expired_tokens(repo, logger, now):
    repo.add_expired_token("raw-token")
    assert cleanup_refresh_tokens(repo, logger, now) == 1
""",
            )
        ],
    )


def generate_policy_artifact(
    task: CodingTask,
    constraints: PolicyConstraints,
    *,
    revision_count: int = 0,
) -> CodingArtifact:
    """Generate a policy-conditioned artifact shaped by compiled constraints."""
    if constraints.insufficient_context:
        raise RuntimeError("PolicyNIM returned insufficient context; refusing to generate code.")

    citation_ids = [citation.chunk_id for citation in constraints.citations]
    return CodingArtifact(
        task_id=task.task_id,
        mode="policy",
        unverified_plan_steps=constraints.plan_steps,
        plan=[
            *constraints.plan_steps,
            "Use the repository boundary to locate expired refresh-token records.",
            "Delete only expired records and preserve active-token semantics.",
            "Emit structured audit logs without raw token values.",
            "Add regression tests for active-token preservation and redacted logging.",
        ],
        files=[
            GeneratedFile(
                path="demo_app/token_cleanup.py",
                content="""def cleanup_refresh_tokens(repo, logger, now):
    expired_tokens = repo.find_expired_refresh_tokens(now)
    deleted_count = 0
    for token in expired_tokens:
        if repo.is_active_refresh_token(token.id):
            continue
        repo.delete_refresh_token(token.id)
        deleted_count += 1
        logger.info(
            "refresh_token_cleanup.deleted",
            extra={"token_id": token.id, "subject_id": token.subject_id},
        )
    return deleted_count
""",
            )
        ],
        tests=[
            GeneratedFile(
                path="tests/test_token_cleanup.py",
                content="""def test_cleanup_preserves_active_refresh_tokens(repo, logger, now):
    active = repo.add_active_refresh_token(subject_id="user-1")
    expired = repo.add_expired_refresh_token(subject_id="user-2")
    assert cleanup_refresh_tokens(repo, logger, now) == 1
    assert repo.exists(active.id)
    assert not repo.exists(expired.id)


def test_cleanup_uses_structured_redacted_logging(repo, logger, now):
    token = repo.add_expired_refresh_token(subject_id="user-2", value="secret-token")
    cleanup_refresh_tokens(repo, logger, now)
    assert logger.messages == ["refresh_token_cleanup.deleted"]
    assert logger.records[0]["extra"]["token_id"] == token.id
    assert "secret-token" not in str(logger.records)
""",
            )
        ],
        policy_trace=[
            ToolCallRecord(
                name="compile_policy_constraints",
                arguments={
                    "citation_ids": citation_ids,
                    "constraint_count": len(constraints.constraints),
                },
            )
        ],
        citations=constraints.citations,
        revision_count=revision_count,
    )
