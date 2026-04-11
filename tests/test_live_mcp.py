"""Opt-in live smoke tests for hosted PolicyNIM MCP."""

from __future__ import annotations

import os

import pytest

from policynim_nemo_workflow.mcp_client import HostedPolicyMcpClient
from policynim_nemo_workflow.settings import DemoSettings

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.getenv("POLICYNIM_BETA_MCP_URL"),
        reason="POLICYNIM_BETA_MCP_URL is not configured.",
    ),
    pytest.mark.skipif(
        not os.getenv("POLICYNIM_BETA_MCP_TOKEN"),
        reason="POLICYNIM_BETA_MCP_TOKEN is not configured.",
    ),
]


@pytest.mark.asyncio
async def test_hosted_mcp_lists_policy_tools_live() -> None:
    tools = await HostedPolicyMcpClient(DemoSettings()).list_tools()

    assert {"policy_preflight", "policy_search"}.issubset(set(tools))


@pytest.mark.asyncio
async def test_hosted_policy_preflight_returns_citations_live() -> None:
    result = await HostedPolicyMcpClient(DemoSettings()).policy_preflight(
        task="Implement refresh-token cleanup.",
        domain="security",
        top_k=3,
    )

    assert result.citations
    assert result.insufficient_context is False
