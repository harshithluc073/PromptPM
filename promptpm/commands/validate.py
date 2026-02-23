"""Implementation for `promptpm validate`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import ValidationError
from promptpm.core.schema import load_prompt_module, validate_prompt_module
from promptpm.utils.output import emit, resolve_output_mode

VALIDATION_EXIT_CODE = 1
INTERNAL_EXIT_CODE = 5
SUCCESS_EXIT_CODE = 0


def _validation_error_payload(path: str, err: ValidationError) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Fix the module definition and run `promptpm validate` again.",
            "path": os.path.abspath(path),
        },
    }


def _internal_error_payload(path: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": os.path.abspath(path),
        },
    }


@click.command(name="validate")
@click.argument("path", default=".")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(ctx: click.Context, path: str, json_output: bool, pretty_output: bool) -> None:
    """Validate a prompt module against schema and semantic rules."""
    merged_json = json_output or bool(ctx.obj and ctx.obj.get("json_output"))
    merged_pretty = pretty_output or bool(ctx.obj and ctx.obj.get("pretty_output"))
    merged_quiet = bool(ctx.obj and ctx.obj.get("quiet"))
    output_mode = resolve_output_mode(
        json_output=merged_json,
        pretty_output=merged_pretty,
    )

    try:
        module = load_prompt_module(path)
        validate_prompt_module(module)
    except ValidationError as err:
        payload = _validation_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(VALIDATION_EXIT_CODE)
    except Exception as err:  # pragma: no cover - defensive path
        payload = _internal_error_payload(path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(INTERNAL_EXIT_CODE)

    payload = {
        "ok": True,
        "data": {
            "path": os.path.abspath(path),
            "source": os.path.abspath(module.source_path),
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
