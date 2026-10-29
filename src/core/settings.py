"""Application settings: local env var injection and typed settings objects."""

import os
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from src.core.env_loader import load_env_files

AZURE = any(os.getenv(var) for var in ["WEBSITE_NAME", "WEBSITE_HOSTNAME", "WEBSITE_DEPLOYMENT_ID"])


if not AZURE:
    load_env_files()


class AzureOpenAISettings(BaseSettings):
    """Connection settings for the Azure OpenAI client."""

    endpoint: str = Field()
    api_key: SecretStr = Field()
    deployment: str = Field()
    api_version: str = Field()

    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_", extra="ignore")


class GitHubSettings(BaseSettings):
    """Credentials for the GitHub API and webhook."""

    token: SecretStr | None = None
    webhook_secret: SecretStr | None = None

    model_config = SettingsConfigDict(env_prefix="GITHUB_", extra="ignore")


class ResilienceSettings(BaseSettings):
    """Retry, backoff and timeout settings shared by the external clients."""

    max_retries: int = Field(ge=0)
    backoff_initial_seconds: float = Field(gt=0)
    backoff_max_seconds: float = Field(gt=0)
    request_timeout_seconds: float = Field(gt=0)

    model_config = SettingsConfigDict(env_prefix="RESILIENCE_", extra="ignore")


class AgentPolicySettings(BaseSettings):
    """Operational limits and permissions of an agent; subclasses only set the env prefix."""

    agent_id: str = Field()
    allowed_tools: Annotated[list[str], NoDecode] = Field()
    max_retrieval_attempts: int = Field(ge=0)
    max_tool_retries: int = Field(ge=0)
    max_tokens: int = Field(gt=0)
    max_cost_usd: float = Field(gt=0)
    max_runtime_seconds: int = Field(gt=0)
    min_available_context_tokens: int = Field(ge=0)

    model_config = SettingsConfigDict(extra="ignore")

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def split_allowed_tools(cls, value: object) -> object:
        """Turn the comma-separated env value into a list."""
        if isinstance(value, str):
            return [tool.strip() for tool in value.split(",") if tool.strip()]
        return value


class SecurityExpertSettings(AgentPolicySettings):
    """Policy of the Security Expert."""

    model_config = SettingsConfigDict(env_prefix="SECURITY_EXPERT_")


class TestArchitectSettings(AgentPolicySettings):
    """Policy of the Test Architect."""

    __test__ = False  # stop pytest from collecting this class because of its Test prefix

    model_config = SettingsConfigDict(env_prefix="TEST_ARCHITECT_")


class HygieneExpertSettings(AgentPolicySettings):
    """Policy of the Hygiene Expert."""

    model_config = SettingsConfigDict(env_prefix="HYGIENE_EXPERT_")


class LogicExpertSettings(AgentPolicySettings):
    """Policy of the Logic Expert."""

    model_config = SettingsConfigDict(env_prefix="LOGIC_EXPERT_")


class PerformanceExpertSettings(AgentPolicySettings):
    """Policy of the Performance Expert."""

    model_config = SettingsConfigDict(env_prefix="PERFORMANCE_EXPERT_")


class Settings(BaseSettings):
    """Root settings object of the application."""

    log_level: str = Field()
    retrieval_cache_ttl_seconds: int = Field(gt=0)

    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    resilience: ResilienceSettings = Field(default_factory=ResilienceSettings)

    security_expert: SecurityExpertSettings = Field(default_factory=SecurityExpertSettings)
    test_architect: TestArchitectSettings = Field(default_factory=TestArchitectSettings)
    hygiene_expert: HygieneExpertSettings = Field(default_factory=HygieneExpertSettings)
    logic_expert: LogicExpertSettings = Field(default_factory=LogicExpertSettings)
    performance_expert: PerformanceExpertSettings = Field(default_factory=PerformanceExpertSettings)

    model_config = SettingsConfigDict(extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them."""
    return Settings()
