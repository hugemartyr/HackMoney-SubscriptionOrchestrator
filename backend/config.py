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


settings = Settings()

