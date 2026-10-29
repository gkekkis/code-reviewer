"""Tools of the Security Expert, as the model sees them."""

import re

from pydantic import BaseModel, Field

from src.application.ports.models import ToolDescription


class DetectExposedSecretsArgs(BaseModel):
    """Arguments the model chooses for detect_exposed_secrets."""

    file_path: str = Field(description="Path of a file changed in the diff, e.g. app/services/fx.py")


class CheckDependencyArgs(BaseModel):
    """Arguments the model chooses for check_dependency."""

    package: str = Field(description="Package name as pinned in the requirements, e.g. requests")
    version: str = Field(description="Exact pinned version, e.g. 2.19.1")


DETECT_EXPOSED_SECRETS = ToolDescription(
    name="detect_exposed_secrets",
    description="Find potential hardcoded secrets (API keys, passwords, tokens) in the added lines of a file "
    "changed in the diff.",
    arguments=DetectExposedSecretsArgs,
)

CHECK_DEPENDENCY = ToolDescription(
    name="check_dependency",
    description="Check an exact package version against known vulnerabilities.",
    arguments=CheckDependencyArgs,
)


SECRET_PATTERN = re.compile(
    r"""(?i)(?:api[_-]?key|secret|password|token|access[_-]?key)\b
    \s*[:=]\s*["']([^"']{4,})["']""",
    re.VERBOSE,
)

KNOWN_VULNERABILITIES = {
    "requests": {"2.19.1": "CVE-2018-18074"},
    "urllib3": {"1.26.4": "CVE-2021-33503"},
    "django": {"3.2.0": "CVE-2021-35042"},
}


def detect_exposed_secrets(file_path: str, diff: str) -> list[str]:
    """Find potential hardcoded secrets in added lines of a Git diff."""
    matches = []
    current_file = None

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue

        if current_file != file_path:
            continue

        if line.startswith("+") and not line.startswith("+++") and SECRET_PATTERN.search(line[1:]):
            matches.append(line[1:].strip())

    return matches


def check_dependency(package: str, version: str) -> str:
    """Check an exact package version against known vulnerabilities."""
    package = package.lower().replace("_", "-")
    cve = KNOWN_VULNERABILITIES.get(package, {}).get(version)

    if cve:
        return f"VULNERABLE: {package}=={version} ({cve})"

    return f"No known vulnerability in local database for {package}=={version}"
