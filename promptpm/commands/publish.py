"""Implementation for `promptpm publish`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import DependencyError, PublishConflictError, ValidationError
from promptpm.core.registry import LocalRegistry
from promptpm.core.schema import load_prompt_module, validate_prompt_module
from promptpm.core.test_runner import TestRunResult, run_prompt_module_tests
from promptpm.utils.output import emit, resolve_output_mode

SUCCESS_EXIT_CODE = 0
VALIDATION_EXIT_CODE = 1
TEST_FAILURE_EXIT_CODE = 2
DEPENDENCY_EXIT_CODE = 3
PUBLISH_CONFLICT_EXIT_CODE = 4
INTERNAL_EXIT_CODE = 5


def _ensure_local_registry_path(raw_path: str) -> str:
    normalized = raw_path.strip()
    if "://" in normalized or normalized.startswith(("http:", "https:")):
        raise DependencyError(
            f"Registry must be a local filesystem path, got: {raw_path!r}"
        )
    return os.path.abspath(normalized)


def _validation_error_payload(path: str, err: ValidationError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "publish",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Fix module validation issues before publishing.",
            "path": os.path.abspath(path),
        },
    }


def _dependency_error_payload(path: str, err: DependencyError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "publish",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Use a valid local registry path and retry.",
            "path": os.path.abspath(path),
        },
    }


def _publish_conflict_payload(path: str, err: PublishConflictError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "publish",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Bump module version before publishing again.",
            "path": os.path.abspath(path),
        },
    }


def _internal_error_payload(path: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "publish",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": os.path.abspath(path),
        },
    }


def _serialize_test_summary(result: TestRunResult) -> Dict[str, int]:
    return {
        "total": result.total,
        "passed": result.passed,
        "failed": result.failed,
    }


def _test_failure_payload(path: str, result: TestRunResult) -> Dict[str, Any]:
    first_failure = None
    for case in result.results:
        if case.failures:
            first_failure = case.failures[0]
            break

    if first_failure is not None:
        message = (
            f"{result.failed} test(s) failed. First failure in "
            f"{first_failure.test_name} at assertion {first_failure.assertion_index} "
            f"({first_failure.assertion_type}): {first_failure.message}"
        )
    else:
        message = f"{result.failed} test(s) failed."

    failures: list[Dict[str, Any]] = []
    for case in result.results:
        for failure in case.failures:
            failures.append(
                {
                    "test_name": failure.test_name,
                    "assertion_index": failure.assertion_index,
                    "assertion_type": failure.assertion_type,
                    "message": failure.message,
                    "expected": failure.expected,
                    "actual": failure.actual,
                }
            )

    return {
        "ok": False,
        "operation": "publish",
        "error": {
            "code": "TEST_FAILURE",
            "message": message,
            "hint": "Fix failing tests before publishing.",
            "path": os.path.abspath(path),
        },
        "data": {
            "tests": _serialize_test_summary(result),
            "failures": failures,
        },
    }


@click.command(name="publish")
@click.argument("path", default=".")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(ctx: click.Context, path: str, json_output: bool, pretty_output: bool) -> None:
    """Validate, test, and publish a module to the local registry."""
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

        module = load_prompt_module(path)
        validate_prompt_module(module)

        test_result = run_prompt_module_tests(path)
        if test_result.failed > 0:
            payload = _test_failure_payload(path, test_result)
            emit(payload, mode=output_mode, quiet=merged_quiet)
            raise SystemExit(TEST_FAILURE_EXIT_CODE)

        module_name = str(module.module["name"])
        module_version = str(module.module["version"])
        if registry.has_version(module_name, module_version):
            raise PublishConflictError(
                f"Published version already exists: {module_name}@{module_version}"
            )

        installed = registry.install(path)
    except ValidationError as err:
        payload = _validation_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(VALIDATION_EXIT_CODE)
    except PublishConflictError as err:
        payload = _publish_conflict_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(PUBLISH_CONFLICT_EXIT_CODE)
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
        "operation": "publish",
        "data": {
            "module_path": os.path.abspath(path),
            "registry_path": registry_path,
            "name": installed.name,
            "version": installed.version,
            "published_path": installed.path,
            "identifier": f"{installed.name}@{installed.version}",
            "tests": _serialize_test_summary(test_result),
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
