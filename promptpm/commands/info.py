"""Implementation for `promptpm info`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import DependencyError, ValidationError
from promptpm.core.registry import InstalledModule, LocalRegistry
from promptpm.core.schema import load_prompt_module, validate_prompt_module
from promptpm.utils.output import emit, resolve_output_mode

SUCCESS_EXIT_CODE = 0
VALIDATION_EXIT_CODE = 1
DEPENDENCY_EXIT_CODE = 3
INTERNAL_EXIT_CODE = 5


def _ensure_local_registry_path(raw_path: str) -> str:
    normalized = raw_path.strip()
    if "://" in normalized or normalized.startswith(("http:", "https:")):
        raise DependencyError(
            f"Registry must be a local filesystem path, got: {raw_path!r}"
        )
    return os.path.abspath(normalized)


def _validation_error_payload(module_name: str, err: ValidationError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "info",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Ensure installed module metadata and interface are valid.",
            "path": module_name,
        },
    }


def _dependency_error_payload(module_name: str, err: DependencyError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "info",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Use a valid local registry path and a module name that exists.",
            "path": module_name,
        },
    }


def _internal_error_payload(module_name: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "info",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": module_name,
        },
    }


def _serialize_module_info(installed: InstalledModule) -> Dict[str, Any]:
    loaded = load_prompt_module(installed.path)
    validate_prompt_module(loaded)
    return {
        "name": installed.name,
        "version": installed.version,
        "source": installed.path,
        "metadata": loaded.module,
        "interface": loaded.interface,
    }


@click.command(name="info")
@click.argument("module_name")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(ctx: click.Context, module_name: str, json_output: bool, pretty_output: bool) -> None:
    """Display metadata and semantic interface for an installed module."""
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
        installed_versions = registry.list_by_name(module_name)
        if not installed_versions:
            raise DependencyError(f"Module not found: {module_name}")

        versions = [_serialize_module_info(item) for item in installed_versions]
    except ValidationError as err:
        payload = _validation_error_payload(module_name, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(VALIDATION_EXIT_CODE)
    except DependencyError as err:
        payload = _dependency_error_payload(module_name, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(DEPENDENCY_EXIT_CODE)
    except Exception as err:  # pragma: no cover - defensive path
        payload = _internal_error_payload(module_name, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(INTERNAL_EXIT_CODE)

    payload = {
        "ok": True,
        "operation": "info",
        "data": {
            "registry_path": registry_path,
            "name": module_name,
            "count": len(versions),
            "versions": versions,
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
