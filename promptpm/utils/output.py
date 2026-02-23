"""Deterministic CLI output helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, Literal, Mapping

OutputMode = Literal["default", "json", "pretty"]


def resolve_output_mode(*, json_output: bool, pretty_output: bool) -> OutputMode:
    """Resolve output mode from flags."""
    if json_output:
        return "json"
    if pretty_output:
        return "pretty"
    return "default"


def emit(payload: Mapping[str, Any], *, mode: OutputMode, quiet: bool = False) -> None:
    """Emit payload using the selected deterministic output mode."""
    if quiet and payload.get("ok") is True:
        return
    print(format_payload(payload, mode=mode))


def format_payload(payload: Mapping[str, Any], *, mode: OutputMode) -> str:
    """Format payload deterministically."""
    if mode == "json":
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if mode == "pretty":
        return _format_pretty(payload)
    return _format_default(payload)


def _format_default(payload: Mapping[str, Any]) -> str:
    if payload.get("ok") is True:
        data = payload.get("data")
        if isinstance(data, dict):
            if "path" in data and "source" in data and len(data) <= 2:
                return (
                    "OK "
                    f"path={_encode(data.get('path', ''))} "
                    f"source={_encode(data.get('source', ''))}"
                )
            return f"OK data={_encode(data)}"
        return f"OK payload={_encode(payload)}"

    error = payload.get("error")
    if isinstance(error, dict):
        if {"code", "path", "message", "hint"}.issubset(set(error)):
            line = (
                "ERROR "
                f"code={_encode(error.get('code', 'UNKNOWN_ERROR'))} "
                f"path={_encode(error.get('path', ''))} "
                f"message={_encode(error.get('message', ''))} "
                f"hint={_encode(error.get('hint', ''))}"
            )
            if payload.get("operation") == "test":
                data = payload.get("data")
                if isinstance(data, dict) and isinstance(data.get("failures"), list):
                    line += f" failures={_encode(data.get('failures'))}"
            return line
        return f"ERROR error={_encode(error)}"
    return f"ERROR payload={_encode(payload)}"


def _format_pretty(payload: Mapping[str, Any]) -> str:
    operation = payload.get("operation")
    if payload.get("ok") is True:
        data = payload.get("data")
        if isinstance(data, dict):
            if "path" in data and "source" in data and len(data) <= 2:
                lines = [
                    "Validation succeeded",
                    f"path: {data.get('path', '')}",
                    f"source: {data.get('source', '')}",
                ]
                return "\n".join(lines)

            if operation == "install":
                dependencies = data.get("installed")
                lines = [
                    "Install succeeded",
                    f"module_path: {data.get('module_path', '')}",
                    f"registry_path: {data.get('registry_path', '')}",
                    f"installed_count: {data.get('count', 0)}",
                ]
                if isinstance(dependencies, list):
                    for dependency in dependencies:
                        if isinstance(dependency, dict):
                            name = dependency.get("name", "")
                            version = dependency.get("version", "")
                            lines.append(f"- {name}@{version}")
                return "\n".join(lines)

            if operation == "test":
                lines = [
                    "Test run succeeded",
                    f"module_path: {data.get('module_path', '')}",
                    f"total: {data.get('total', 0)}",
                    f"passed: {data.get('passed', 0)}",
                    f"failed: {data.get('failed', 0)}",
                ]
                results = data.get("results")
                if isinstance(results, list):
                    for result in results:
                        if isinstance(result, dict):
                            status = str(result.get("status", "")).upper()
                            lines.append(f"- {status} {result.get('name', '')}")
                return "\n".join(lines)

        return json.dumps(payload, indent=2, sort_keys=True)

    error = payload.get("error")
    if isinstance(error, dict):
        header = "Validation failed"
        if operation == "install":
            header = "Install failed"
        if operation == "test":
            header = "Test run failed"
        lines = [
            header,
            f"code: {error.get('code', 'UNKNOWN_ERROR')}",
            f"path: {error.get('path', '')}",
            f"message: {error.get('message', '')}",
            f"hint: {error.get('hint', '')}",
        ]
        if operation == "test":
            data = payload.get("data")
            if isinstance(data, dict):
                failures = data.get("failures")
                if isinstance(failures, list):
                    for failure in failures:
                        if isinstance(failure, dict):
                            lines.append(
                                f"- {failure.get('test_name', '')}[{failure.get('assertion_index', '')}] "
                                f"{failure.get('assertion_type', '')}: {failure.get('message', '')}"
                            )
        return "\n".join(lines)
    return json.dumps(payload, indent=2, sort_keys=True)


def _encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
