"""Runtime settings for the demo CLI."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    """Environment-backed settings for hosted-only live runs."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    policynim_beta_mcp_url: str | None = Field(
        default=None,
        validation_alias="POLICYNIM_BETA_MCP_URL",
    )
    policynim_beta_mcp_token: str | None = Field(
        default=None,
        validation_alias="POLICYNIM_BETA_MCP_TOKEN",
    )
    nvidia_api_key: str | None = Field(default=None, validation_alias="NVIDIA_API_KEY")
    nim_model: str = Field(default="meta/llama-3.1-70b-instruct", validation_alias="NIM_MODEL")

    @field_validator(
        "policynim_beta_mcp_url",
        "policynim_beta_mcp_token",
        "nvidia_api_key",
        mode="before",
    )
    @classmethod
    def normalize_optional_env(cls, value: object) -> object:
        """Treat blank env vars as unset so failures are explicit."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def require_hosted_mcp(self) -> None:
        """Fail fast when hosted MCP settings are missing."""
        missing = [
            name
            for name, value in (
                ("POLICYNIM_BETA_MCP_URL", self.policynim_beta_mcp_url),
                ("POLICYNIM_BETA_MCP_TOKEN", self.policynim_beta_mcp_token),
            )
            if value is None
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Hosted PolicyNIM MCP settings are missing: {joined}.")

    def require_nvidia(self) -> None:
        """Fail fast when NVIDIA settings are missing."""
        if self.nvidia_api_key is None:
            raise RuntimeError("NVIDIA_API_KEY is required for live NIM-backed generation.")
