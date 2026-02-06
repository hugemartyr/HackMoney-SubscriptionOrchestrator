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

    # Google Gemini model configuration
    GOOGLE_API_KEY: str | None = _os.getenv("GOOGLE_API_KEY")
    GOOGLE_MODEL: str = _os.getenv("GOOGLE_MODEL", "gemini-3-flash-preview")
    
    GOOGLE_PRO_MODEL: str = _os.getenv("GOOGLE_PRO_MODEL", "gemini-3-pro-preview")


settings = Settings()

