"""Semantic version parsing, comparison, and range matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal


_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

_IDENTIFIER_PATTERN = re.compile(r"^[0-9A-Za-z-]+$")

ComparatorOperator = Literal["<", "<=", ">", ">=", "="]


class SemVerError(ValueError):
    """Raised when semantic version or range parsing fails."""


@dataclass(frozen=True)
class SemanticVersion:
    """Semantic version following SemVer precedence rules."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_numeric_field(self.major, "major")
        _validate_numeric_field(self.minor, "minor")
        _validate_numeric_field(self.patch, "patch")
        _validate_identifiers(self.prerelease, "prerelease", check_numeric_leading_zero=True)
        _validate_identifiers(self.build, "build", check_numeric_leading_zero=False)

    @classmethod
    def parse(cls, value: str) -> SemanticVersion:
        """Parse a semantic version string."""
        if not isinstance(value, str):
            raise SemVerError("Semantic version must be a string")

        normalized = value.strip()
        match = _SEMVER_PATTERN.fullmatch(normalized)
        if not match:
            raise SemVerError(f"Invalid semantic version: {value!r}")

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
        build = tuple(match.group(5).split(".")) if match.group(5) else ()

        return cls(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            build=build,
        )

    def compare_to(self, other: SemanticVersion) -> int:
        """Compare this version against another semantic version."""
        if not isinstance(other, SemanticVersion):
            raise SemVerError("Can only compare SemanticVersion to SemanticVersion")

        core_self = (self.major, self.minor, self.patch)
        core_other = (other.major, other.minor, other.patch)
        if core_self < core_other:
            return -1
        if core_self > core_other:
            return 1
        return _compare_prerelease(self.prerelease, other.prerelease)

    def __str__(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            value += f"-{'.'.join(self.prerelease)}"
        if self.build:
            value += f"+{'.'.join(self.build)}"
        return value


@dataclass(frozen=True)
class VersionComparator:
    """Single comparator clause in a semantic version range."""

    operator: ComparatorOperator
    version: SemanticVersion

    def matches(self, candidate: SemanticVersion) -> bool:
        cmp_value = candidate.compare_to(self.version)
        if self.operator == "<":
            return cmp_value < 0
        if self.operator == "<=":
            return cmp_value <= 0
        if self.operator == ">":
            return cmp_value > 0
        if self.operator == ">=":
            return cmp_value >= 0
        return cmp_value == 0


@dataclass(frozen=True)
class VersionRange:
    """
    Semantic version range.

    Range alternatives are OR-ed groups; each group is an AND of comparators.
    """

    alternatives: tuple[tuple[VersionComparator, ...], ...]

    def matches(self, version: SemanticVersion | str) -> bool:
        candidate = _coerce_version(version)
        for alternative in self.alternatives:
            if all(comparator.matches(candidate) for comparator in alternative):
                return True
        return False


def parse_version(value: str) -> SemanticVersion:
    """Parse a semantic version string."""
    return SemanticVersion.parse(value)


def compare_versions(left: SemanticVersion | str, right: SemanticVersion | str) -> int:
    """Compare two semantic versions, returning -1, 0, or 1."""
    left_version = _coerce_version(left)
    right_version = _coerce_version(right)
    return left_version.compare_to(right_version)


def parse_version_range(expression: str) -> VersionRange:
    """
    Parse semantic version ranges.

    Supported tokens:
    - exact: `1.2.3`
    - comparator: `<1.2.3`, `<=1.2.3`, `>1.2.3`, `>=1.2.3`, `=1.2.3`
    - caret: `^1.2.3`
    - tilde: `~1.2.3`
    - wildcard: `*`
    - AND separators: space or comma
    - OR separator: `||`
    """
    if not isinstance(expression, str):
        raise SemVerError("Version range must be a string")

    normalized = expression.strip()
    if not normalized or normalized == "*":
        return VersionRange(alternatives=(tuple(),))

    alternatives: list[tuple[VersionComparator, ...]] = []
    for alternative_text in (part.strip() for part in normalized.split("||")):
        if not alternative_text:
            raise SemVerError(f"Invalid semantic version range: {expression!r}")

        tokens = [token for token in alternative_text.replace(",", " ").split() if token]
        if not tokens:
            raise SemVerError(f"Invalid semantic version range: {expression!r}")

        comparators: list[VersionComparator] = []
        for token in tokens:
            comparators.extend(_parse_range_token(token))
        alternatives.append(tuple(comparators))

    return VersionRange(alternatives=tuple(alternatives))


def satisfies_version_range(version: SemanticVersion | str, expression: str) -> bool:
    """Return True when version satisfies the provided range expression."""
    parsed_range = parse_version_range(expression)
    return parsed_range.matches(version)


def _coerce_version(value: SemanticVersion | str) -> SemanticVersion:
    if isinstance(value, SemanticVersion):
        return value
    return parse_version(value)


def _parse_range_token(token: str) -> list[VersionComparator]:
    if token == "*":
        return []

    if token.startswith("^"):
        base = parse_version(token[1:])
        return [
            VersionComparator(operator=">=", version=base),
            VersionComparator(operator="<", version=_caret_upper_bound(base)),
        ]

    if token.startswith("~"):
        base = parse_version(token[1:])
        upper = SemanticVersion(major=base.major, minor=base.minor + 1, patch=0)
        return [
            VersionComparator(operator=">=", version=base),
            VersionComparator(operator="<", version=upper),
        ]

    for operator in (">=", "<=", ">", "<", "="):
        if token.startswith(operator):
            version_text = token[len(operator):]
            if not version_text:
                raise SemVerError(f"Invalid range token: {token!r}")
            return [VersionComparator(operator=operator, version=parse_version(version_text))]

    return [VersionComparator(operator="=", version=parse_version(token))]


def _caret_upper_bound(base: SemanticVersion) -> SemanticVersion:
    if base.major > 0:
        return SemanticVersion(major=base.major + 1, minor=0, patch=0)
    if base.minor > 0:
        return SemanticVersion(major=0, minor=base.minor + 1, patch=0)
    return SemanticVersion(major=0, minor=0, patch=base.patch + 1)


def _compare_prerelease(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1

    for left_identifier, right_identifier in zip(left, right):
        if left_identifier == right_identifier:
            continue

        left_is_numeric = left_identifier.isdigit()
        right_is_numeric = right_identifier.isdigit()

        if left_is_numeric and right_is_numeric:
            left_value = int(left_identifier)
            right_value = int(right_identifier)
            if left_value < right_value:
                return -1
            if left_value > right_value:
                return 1
            continue

        if left_is_numeric and not right_is_numeric:
            return -1
        if not left_is_numeric and right_is_numeric:
            return 1

        if left_identifier < right_identifier:
            return -1
        if left_identifier > right_identifier:
            return 1

    if len(left) < len(right):
        return -1
    if len(left) > len(right):
        return 1
    return 0


def _validate_numeric_field(value: int, field_name: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise SemVerError(f"{field_name} must be a non-negative integer")


def _validate_identifiers(
    identifiers: tuple[str, ...],
    field_name: str,
    *,
    check_numeric_leading_zero: bool,
) -> None:
    if not isinstance(identifiers, tuple):
        raise SemVerError(f"{field_name} identifiers must be a tuple")

    for identifier in identifiers:
        if not isinstance(identifier, str) or not identifier:
            raise SemVerError(f"{field_name} identifiers must be non-empty strings")
        if not _IDENTIFIER_PATTERN.fullmatch(identifier):
            raise SemVerError(f"Invalid {field_name} identifier: {identifier!r}")
        if check_numeric_leading_zero and identifier.isdigit():
            if len(identifier) > 1 and identifier.startswith("0"):
                raise SemVerError(
                    f"Invalid semantic version: numeric {field_name} identifier "
                    f"has leading zero: {identifier!r}"
                )

