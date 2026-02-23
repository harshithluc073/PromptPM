"""Implementation for `promptpm install`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import DependencyError, ValidationError
from promptpm.core.registry import LocalRegistry
from promptpm.core.resolver import DependencyResolver, ResolvedDependency
from promptpm.utils.output import emit, resolve_output_mode

SUCCESS_EXIT_CODE = 0
VALIDATION_EXIT_CODE = 1
DEPENDENCY_EXIT_CODE = 3
INTERNAL_EXIT_CODE = 5


def _validation_error_payload(path: str, err: ValidationError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "install",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Fix module validation issues before installing dependencies.",
            "path": os.path.abspath(path),
        },
    }


def _dependency_error_payload(path: str, err: DependencyError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "install",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": (
                "Ensure all dependencies are available in the local registry and "
                "dependency version ranges are valid."
            ),
            "path": os.path.abspath(path),
        },
    }


def _internal_error_payload(path: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "install",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": os.path.abspath(path),
        },
    }


def _ensure_local_registry_path(raw_path: str) -> str:
    normalized = raw_path.strip()
    if "://" in normalized or normalized.startswith(("http:", "https:")):
        raise DependencyError(
            f"Registry must be a local filesystem path, got: {raw_path!r}"
        )
    return os.path.abspath(normalized)


def _serialize_resolved_dependencies(
    dependencies: tuple[ResolvedDependency, ...],
) -> list[Dict[str, str]]:
    serialized: list[Dict[str, str]] = []
    for dependency in dependencies:
        serialized.append(
            {
                "name": dependency.name,
                "version": dependency.version,
                "path": dependency.path,
            }
        )
    return serialized


@click.command(name="install")
@click.argument("path", default=".")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(ctx: click.Context, path: str, json_output: bool, pretty_output: bool) -> None:
    """Resolve module dependencies from the local registry."""
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
        resolver = DependencyResolver(LocalRegistry(registry_path))
        resolved = resolver.resolve_for_module(path)
    except ValidationError as err:
        payload = _validation_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(VALIDATION_EXIT_CODE)
    except DependencyError as err:
        payload = _dependency_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(DEPENDENCY_EXIT_CODE)
    except Exception as err:  # pragma: no cover - defensive path
        payload = _internal_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(INTERNAL_EXIT_CODE)

    payload = {
        "ok": True,
        "operation": "install",
        "data": {
            "module_path": os.path.abspath(path),
            "registry_path": registry_path,
            "installed": _serialize_resolved_dependencies(resolved),
            "count": len(resolved),
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
