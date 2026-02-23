"""Implementation for `promptpm list`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import DependencyError
from promptpm.core.registry import InstalledModule, LocalRegistry
from promptpm.utils.output import emit, resolve_output_mode

SUCCESS_EXIT_CODE = 0
DEPENDENCY_EXIT_CODE = 3
INTERNAL_EXIT_CODE = 5


def _ensure_local_registry_path(raw_path: str) -> str:
    normalized = raw_path.strip()
    if "://" in normalized or normalized.startswith(("http:", "https:")):
        raise DependencyError(
            f"Registry must be a local filesystem path, got: {raw_path!r}"
        )
    return os.path.abspath(normalized)


def _dependency_error_payload(registry_path: str, err: DependencyError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "list",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Use a valid local registry path and verify installed module integrity.",
            "path": registry_path,
        },
    }


def _internal_error_payload(registry_path: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "list",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": registry_path,
        },
    }


def _serialize_modules(modules: tuple[InstalledModule, ...]) -> list[Dict[str, str]]:
    items: list[Dict[str, str]] = []
    for module in modules:
        items.append(
            {
                "name": module.name,
                "version": module.version,
                "source": module.path,
            }
        )
    return items


@click.command(name="list")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(ctx: click.Context, json_output: bool, pretty_output: bool) -> None:
    """List installed modules from the local registry."""
    merged_json = json_output or bool(ctx.obj and ctx.obj.get("json_output"))
    merged_pretty = pretty_output or bool(ctx.obj and ctx.obj.get("pretty_output"))
    merged_quiet = bool(ctx.obj and ctx.obj.get("quiet"))
    output_mode = resolve_output_mode(
        json_output=merged_json,
        pretty_output=merged_pretty,
    )

    registry_raw = ".promptpm_registry"
    if ctx.obj and isinstance(ctx.obj.get("registry_path"), str):
        registry_raw = str(ctx.obj["registry_path"])

    try:
        registry_path = _ensure_local_registry_path(registry_raw)
        registry = LocalRegistry(registry_path)
        installed = registry.list_installed()
    except DependencyError as err:
        payload = _dependency_error_payload(registry_raw, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(DEPENDENCY_EXIT_CODE)
    except Exception as err:  # pragma: no cover - defensive path
        payload = _internal_error_payload(registry_raw, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(INTERNAL_EXIT_CODE)

    payload = {
        "ok": True,
        "operation": "list",
        "data": {
            "registry_path": registry_path,
            "count": len(installed),
            "modules": _serialize_modules(installed),
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
