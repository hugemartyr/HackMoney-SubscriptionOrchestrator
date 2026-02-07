from pathlib import Path


class Settings:
    # Git clone controls
    import os as _os
    GIT_CLONE_TIMEOUT_SECONDS: int = int(_os.getenv("GIT_CLONE_TIMEOUT_SECONDS", "300"))

    # Local sandbox root (single-session)
    # Fixed to <repo>/backend/sandbox (no env override)
    SANDBOX_DIR: str = str((Path(__file__).resolve().parent / "sandbox"))

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = _os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")

    # OpenRouter (LLM) – used for all agent LLM calls (e.g. Claude Sonnet)
    OPENROUTER_API_KEY: str | None = _os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = _os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder-next")

    # Legacy Google Gemini (optional; kept for embeddings or fallback)
    GOOGLE_API_KEY: str | None = _os.getenv("GOOGLE_API_KEY")
    GOOGLE_MODEL: str = _os.getenv("GOOGLE_MODEL", "gemini-3-flash-preview")
    GOOGLE_PRO_MODEL: str = _os.getenv("GOOGLE_PRO_MODEL", "gemini-3-pro-preview")


settings = Settings()

