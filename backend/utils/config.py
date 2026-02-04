from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    log_level: str
    llm_provider: str
    llm_model: str
    llm_api_key: str
    llm_base_url: str
    llm_policy: str


_config: AppConfig | None = None


def load_config() -> AppConfig:
    global _config
    if _config is not None:
        return _config

    load_dotenv()

    _config = AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "info"),
        llm_provider=os.getenv("LLM_PROVIDER", "gemini"),
        llm_model=os.getenv("LLM_MODEL", "gemini-1.5-pro"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_policy=os.getenv("LLM_POLICY", "default"),
    )
    return _config
