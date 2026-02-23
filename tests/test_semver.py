"""Unit tests for semantic version parsing and range matching."""

from __future__ import annotations

import pytest

from promptpm.core.semver import (
    SemVerError,
    compare_versions,
    parse_version,
    parse_version_range,
    satisfies_version_range,
)


def test_parse_version_with_prerelease_and_build() -> None:
    version = parse_version("1.2.3-alpha.1+build.5")

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.prerelease == ("alpha", "1")
    assert version.build == ("build", "5")
    assert str(version) == "1.2.3-alpha.1+build.5"


@pytest.mark.parametrize(
    "value",
    [
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2",
        "1.2.3-",
    ],
)
def test_parse_version_rejects_invalid_core_format(value: str) -> None:
    with pytest.raises(SemVerError, match="Invalid semantic version"):
        parse_version(value)


def test_parse_version_rejects_numeric_prerelease_leading_zero() -> None:
    with pytest.raises(SemVerError, match="leading zero"):
        parse_version("1.0.0-alpha.01")


def test_compare_versions_semver_precedence_chain() -> None:
    ordered = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]

    for index in range(len(ordered) - 1):
        left = ordered[index]
        right = ordered[index + 1]
        assert compare_versions(left, right) < 0
        assert compare_versions(right, left) > 0


def test_compare_versions_ignores_build_metadata() -> None:
    assert compare_versions("1.2.3+abc", "1.2.3+def") == 0


def test_range_comparator_expression() -> None:
    range_expr = parse_version_range(">=1.2.3 <2.0.0")

    assert range_expr.matches("1.2.3")
    assert range_expr.matches("1.9.9")
    assert not range_expr.matches("2.0.0")
    assert not range_expr.matches("1.2.3-alpha")


def test_range_supports_commas_and_or_alternatives() -> None:
    range_expr = parse_version_range(">=1.0.0, <2.0.0 || >=3.0.0")

    assert range_expr.matches("1.4.0")
    assert not range_expr.matches("2.5.0")
    assert range_expr.matches("3.1.0")


def test_range_supports_caret_rules() -> None:
    assert satisfies_version_range("1.9.9", "^1.2.3")
    assert not satisfies_version_range("2.0.0", "^1.2.3")

    assert satisfies_version_range("0.2.9", "^0.2.3")
    assert not satisfies_version_range("0.3.0", "^0.2.3")

    assert satisfies_version_range("0.0.3", "^0.0.3")
    assert not satisfies_version_range("0.0.4", "^0.0.3")


def test_range_supports_tilde_rules() -> None:
    assert satisfies_version_range("1.2.3", "~1.2.3")
    assert satisfies_version_range("1.2.9", "~1.2.3")
    assert not satisfies_version_range("1.3.0", "~1.2.3")


def test_range_supports_wildcard_and_empty_expression() -> None:
    assert satisfies_version_range("999.999.999", "*")
    assert satisfies_version_range("0.0.1", " ")


@pytest.mark.parametrize(
    "expression",
    [
        "|| 1.2.3",
        "1.2.3 ||",
        "=>1.2.3",
        "^",
    ],
)
def test_range_rejects_invalid_expressions(expression: str) -> None:
    with pytest.raises(SemVerError):
        parse_version_range(expression)

