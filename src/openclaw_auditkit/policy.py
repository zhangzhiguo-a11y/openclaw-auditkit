"""Risk classification policy for repository-relative changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import fnmatch

from .models import RiskClass, normalize_rel_path


DEFAULT_C_PATTERNS = (
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "**/*secret*",
    "**/*token*",
    "**/*credential*",
    "**/*private-key*",
    "**/credentials/**",
    "**/secrets/**",
    "**/oauth/**",
    "**/customer-data/**",
    "**/production-data/**",
)

DEFAULT_B_PATTERNS = (
    ".github/workflows/**",
    "bin/**",
    "scripts/**",
    "src/**",
    "lib/**",
    "packages/**",
    "schemas/**",
    "migrations/**",
    "infra/**",
    "deploy/**",
    "Dockerfile",
    "docker-compose.yml",
    "pyproject.toml",
    "package.json",
)


@dataclass(frozen=True)
class Classification:
    risk_class: RiskClass
    reasons: list[str]
    changed_files: list[str]

    @property
    def requires_audit(self) -> bool:
        return True

    @property
    def requires_closeout_receipt(self) -> bool:
        return self.risk_class == "B"

    @property
    def apply_allowed(self) -> bool:
        return self.risk_class == "A"

    def to_dict(self) -> dict[str, object]:
        return {
            "risk_class": self.risk_class,
            "requires_audit": self.requires_audit,
            "requires_closeout_receipt": self.requires_closeout_receipt,
            "apply_allowed": self.apply_allowed,
            "reasons": self.reasons,
            "changed_files": self.changed_files,
        }


def _matches(path: str, patterns: Iterable[str]) -> list[str]:
    return [pattern for pattern in patterns if fnmatch.fnmatchcase(path, pattern)]


def classify_paths(
    changed_files: Iterable[str],
    *,
    b_patterns: Iterable[str] = DEFAULT_B_PATTERNS,
    c_patterns: Iterable[str] = DEFAULT_C_PATTERNS,
) -> Classification:
    files = [normalize_rel_path(item) for item in changed_files]
    if not files:
        return Classification("A", ["no changed files supplied"], [])

    c_hits: list[str] = []
    b_hits: list[str] = []
    for path in files:
        for pattern in _matches(path, c_patterns):
            c_hits.append(f"{path} matches protected pattern {pattern}")
        for pattern in _matches(path, b_patterns):
            b_hits.append(f"{path} matches review pattern {pattern}")

    if c_hits:
        return Classification("C", c_hits, files)
    if b_hits:
        return Classification("B", b_hits, files)
    return Classification("A", ["all changed files are outside protected and review patterns"], files)
