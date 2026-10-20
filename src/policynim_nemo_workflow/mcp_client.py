"""Hosted PolicyNIM MCP client boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Protocol

import httpx
from mcp.types import TextContent
from pydantic import ValidationError

from policynim_nemo_workflow.models import PolicyPreflightResult
from policynim_nemo_workflow.settings import DemoSettings

if TYPE_CHECKING:
    from mcp import ClientSession


class PolicyClient(Protocol):
    """Minimal hosted PolicyNIM client contract."""

    async def list_tools(self) -> Sequence[str]:
        """Return hosted MCP tool names."""

    async def policy_preflight(
        self,
        *,
        task: str,
        domain: str | None,
        top_k: int,
    ) -> PolicyPreflightResult:
        """Call PolicyNIM policy_preflight."""


class HostedPolicyMcpClient:
    """Client for the hosted PolicyNIM streamable HTTP MCP server."""

    def __init__(self, settings: DemoSettings) -> None:
        settings.require_hosted_mcp()
        self._url = settings.policynim_beta_mcp_url or ""
        self._token = settings.policynim_beta_mcp_token or ""

    async def list_tools(self) -> Sequence[str]:
        """Return hosted MCP tool names."""
        async with self._session() as session:
            result = await session.list_tools()
            return [tool.name for tool in result.tools]

    async def policy_preflight(
        self,
        *,
        task: str,
        domain: str | None,
        top_k: int,
    ) -> PolicyPreflightResult:
        """Call hosted PolicyNIM policy_preflight and validate the structured payload."""
        async with self._session() as session:
            arguments: dict[str, object] = {"task": task, "top_k": top_k}
            if domain is not None:
                arguments["domain"] = domain
            result = await session.call_tool("policy_preflight", arguments)
        if result.isError:
            details = "\n".join(
                block.text for block in result.content if isinstance(block, TextContent)
            )
            if self._token:
                details = details.replace(self._token, "<redacted>")
            details = details[:2000].strip() or "The server returned no recovery details."
            raise RuntimeError(f"PolicyNIM policy_preflight failed: {details}")
        payload = result.structuredContent
        if not isinstance(payload, dict):
            payload_type = type(payload).__name__
            raise RuntimeError(
                f"policy_preflight did not return structured content (received {payload_type})."
            )
        try:
            return PolicyPreflightResult.model_validate(payload)
        except ValidationError as exc:
            raise RuntimeError("policy_preflight returned invalid structured content.") from exc

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        """Open and close one authenticated MCP session."""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        headers = {"Authorization": f"Bearer {self._token}"}
        timeout = httpx.Timeout(30.0, read=300.0)
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as http_client:
            async with streamable_http_client(self._url, http_client=http_client) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
