"""Unit tests for output formatting utilities."""

from __future__ import annotations

import json

from promptpm.utils.output import format_payload, resolve_output_mode


def test_resolve_output_mode_default() -> None:
    assert resolve_output_mode(json_output=False, pretty_output=False) == "default"


def test_resolve_output_mode_json() -> None:
    assert resolve_output_mode(json_output=True, pretty_output=False) == "json"


def test_resolve_output_mode_pretty() -> None:
    assert resolve_output_mode(json_output=False, pretty_output=True) == "pretty"


def test_resolve_output_mode_json_precedence_when_both_flags_set() -> None:
    assert resolve_output_mode(json_output=True, pretty_output=True) == "json"


def test_format_payload_json_is_deterministic() -> None:
    payload = {"b": 1, "a": {"d": 4, "c": 3}}
    formatted = format_payload(payload, mode="json")

    assert formatted == '{"a":{"c":3,"d":4},"b":1}'


def test_format_payload_default_success() -> None:
    payload = {
        "ok": True,
        "data": {
            "path": "C:/tmp/module",
            "source": "C:/tmp/module/promptpm.yaml",
        },
    }
    formatted = format_payload(payload, mode="default")

    assert (
        formatted
        == 'OK path="C:/tmp/module" source="C:/tmp/module/promptpm.yaml"'
    )


def test_format_payload_pretty_error() -> None:
    payload = {
        "ok": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "path": "/tmp/module",
            "message": "bad module",
            "hint": "fix it",
        },
    }
    formatted = format_payload(payload, mode="pretty")

    assert formatted == (
        "Validation failed\n"
        "code: VALIDATION_ERROR\n"
        "path: /tmp/module\n"
        "message: bad module\n"
        "hint: fix it"
    )
