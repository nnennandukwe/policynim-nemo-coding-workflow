"""Hosted MCP client error handling tests."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from policynim_nemo_workflow.mcp_client import HostedPolicyMcpClient


class FakeToolResult:
    def __init__(self, structured_content: object) -> None:
        self.structuredContent = structured_content


class FakeSession:
    def __init__(self, structured_content: object) -> None:
        self._structured_content = structured_content

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> FakeToolResult:
        return FakeToolResult(self._structured_content)


def _client_with_payload(payload: object) -> HostedPolicyMcpClient:
    client = HostedPolicyMcpClient.__new__(HostedPolicyMcpClient)

    @asynccontextmanager
    async def fake_session():
        yield FakeSession(payload)

    client._session = fake_session
    return client


@pytest.mark.asyncio
async def test_policy_preflight_reports_non_dict_structured_content() -> None:
    client = _client_with_payload(["not", "a", "dict"])

    with pytest.raises(RuntimeError, match="received list"):
        await client.policy_preflight(
            task="Implement refresh-token cleanup.",
            domain="security",
            top_k=3,
        )


@pytest.mark.asyncio
async def test_policy_preflight_wraps_invalid_structured_content() -> None:
    client = _client_with_payload({"task": "Implement refresh-token cleanup."})

    with pytest.raises(RuntimeError, match="invalid structured content") as exc_info:
        await client.policy_preflight(
            task="Implement refresh-token cleanup.",
            domain="security",
            top_k=3,
        )

    assert exc_info.value.__cause__ is not None
