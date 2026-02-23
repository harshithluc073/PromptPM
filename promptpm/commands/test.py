"""Implementation for `promptpm test`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import ValidationError
from promptpm.core.test_runner import AssertionFailure, TestRunResult, run_prompt_module_tests
from promptpm.utils.output import emit, resolve_output_mode

SUCCESS_EXIT_CODE = 0
VALIDATION_EXIT_CODE = 1
TEST_FAILURE_EXIT_CODE = 2
INTERNAL_EXIT_CODE = 5


def _validation_error_payload(path: str, err: ValidationError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "test",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Fix module or test schema issues and run `promptpm test` again.",
            "path": os.path.abspath(path),
        },
    }


def _internal_error_payload(path: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "test",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": os.path.abspath(path),
        },
    }


def _serialize_failure(failure: AssertionFailure) -> Dict[str, Any]:
    return {
        "test_name": failure.test_name,
        "assertion_index": failure.assertion_index,
        "assertion_type": failure.assertion_type,
        "message": failure.message,
        "expected": failure.expected,
        "actual": failure.actual,
    }


def _serialize_result(result: TestRunResult) -> Dict[str, Any]:
    failures: list[Dict[str, Any]] = []
    cases: list[Dict[str, Any]] = []
    for case in result.results:
        cases.append(
            {
                "name": case.name,
                "status": "passed" if case.passed else "failed",
                "failure_count": len(case.failures),
            }
        )
        for failure in case.failures:
            failures.append(_serialize_failure(failure))

    return {
        "total": result.total,
        "passed": result.passed,
        "failed": result.failed,
        "results": cases,
        "failures": failures,
    }


def _test_failure_payload(path: str, result: TestRunResult) -> Dict[str, Any]:
    serialized = _serialize_result(result)
    first_failure = serialized["failures"][0] if serialized["failures"] else None
    if isinstance(first_failure, dict):
        message = (
            f"{result.failed} test(s) failed. First failure in "
            f"{first_failure['test_name']} at assertion {first_failure['assertion_index']} "
            f"({first_failure['assertion_type']}): {first_failure['message']}"
        )
    else:
        message = f"{result.failed} test(s) failed."

    return {
        "ok": False,
        "operation": "test",
        "error": {
            "code": "TEST_FAILURE",
            "message": message,
            "hint": "Inspect failure diagnostics and update tests, inputs, or templates.",
            "path": os.path.abspath(path),
        },
        "data": serialized,
    }


@click.command(name="test")
@click.argument("path", default=".")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(ctx: click.Context, path: str, json_output: bool, pretty_output: bool) -> None:
    """Run deterministic prompt module tests."""
    merged_json = json_output or bool(ctx.obj and ctx.obj.get("json_output"))
    merged_pretty = pretty_output or bool(ctx.obj and ctx.obj.get("pretty_output"))
    merged_quiet = bool(ctx.obj and ctx.obj.get("quiet"))
    output_mode = resolve_output_mode(
        json_output=merged_json,
        pretty_output=merged_pretty,
    )

    try:
        result = run_prompt_module_tests(path)
    except ValidationError as err:
        payload = _validation_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(VALIDATION_EXIT_CODE)
    except Exception as err:  # pragma: no cover - defensive path
        payload = _internal_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(INTERNAL_EXIT_CODE)

    if result.failed > 0:
        payload = _test_failure_payload(path, result)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(TEST_FAILURE_EXIT_CODE)

    payload = {
        "ok": True,
        "operation": "test",
        "data": {
            "module_path": os.path.abspath(path),
            **_serialize_result(result),
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
