import re

from pydantic import BaseModel, HttpUrl, field_validator


_GITHUB_REPO_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+(\.git)?/?$")


class UploadRequest(BaseModel):
    github_url: HttpUrl  # e.g. https://github.com/<owner>/<repo> (optional .git)

    @field_validator("github_url")
    @classmethod
    def github_repo_only(cls, v: HttpUrl) -> HttpUrl:
        url = str(v).strip()
        if not _GITHUB_REPO_RE.match(url):
            raise ValueError(
                "Only GitHub repo HTTPS links are allowed: https://github.com/<owner>/<repo> (optional .git)."
            )
        return v


class UploadResponse(BaseModel):
    ok: bool

