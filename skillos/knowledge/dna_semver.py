"""Semver helpers for domain template DNA versions."""

from __future__ import annotations


def parse_semver(version: str) -> tuple[int, int, int]:
    raw = (version or "0.0.0").lstrip("v").strip()
    parts = raw.split(".")
    nums: list[int] = []
    for i in range(3):
        try:
            nums.append(int(parts[i]) if i < len(parts) else 0)
        except ValueError:
            nums.append(0)
    return nums[0], nums[1], nums[2]


def format_semver(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"


def bump_semver(version: str, level: str = "patch") -> str:
    major, minor, patch = parse_semver(version)
    if level == "major":
        return format_semver(major + 1, 0, 0)
    if level == "minor":
        return format_semver(major, minor + 1, 0)
    return format_semver(major, minor, patch + 1)


def compare_semver(a: str, b: str) -> int:
    """Return -1 if a<b, 0 if equal, 1 if a>b."""
    pa, pb = parse_semver(a), parse_semver(b)
    if pa < pb:
        return -1
    if pa > pb:
        return 1
    return 0


def is_stale_version(recorded: str, current: str) -> bool:
    return compare_semver(recorded, current) < 0
