"""Implementation for `promptpm init`."""

from __future__ import annotations

import os
from typing import Any, Dict

import click

from promptpm.core.errors import ValidationError
from promptpm.utils.output import emit, resolve_output_mode

SUCCESS_EXIT_CODE = 0
VALIDATION_EXIT_CODE = 1
INTERNAL_EXIT_CODE = 5


def _validation_error_payload(path: str, err: ValidationError) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "init",
        "error": {
            "code": err.code,
            "message": str(err),
            "hint": "Run `promptpm init` in an empty module directory or remove conflicting files.",
            "path": os.path.abspath(path),
        },
    }


def _internal_error_payload(path: str, err: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "operation": "init",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(err) or "Unexpected internal error",
            "hint": "Retry the command and inspect traceback in debug logs.",
            "path": os.path.abspath(path),
        },
    }


def _default_module_name(path: str) -> str:
    directory_name = os.path.basename(os.path.abspath(path)).strip()
    if directory_name:
        return directory_name
    return "prompt-module"


def _render_promptpm_yaml(*, name: str, version: str) -> str:
    return (
        "module:\n"
        f"  name: {name}\n"
        f"  version: \"{version}\"\n"
        "  description: Describe this module\n"
        "prompt:\n"
        "  template: template.prompt\n"
        "  placeholders:\n"
        "    - document\n"
        "interface:\n"
        "  intent: Describe module intent.\n"
        "  inputs:\n"
        "    - name: document\n"
        "      type: technical_document\n"
        "      description: Source document text\n"
        "      required: true\n"
        "  outputs:\n"
        "    - type: structured_summary\n"
        "      description: Concise technical summary\n"
        "tests:\n"
        "  - name: basic\n"
        "    inputs:\n"
        "      document: example\n"
        "    assertions:\n"
        "      - contains: \"Summary\"\n"
    )


@click.command(name="init")
@click.option("--name", "module_name", default=None, help="Module name.")
@click.option("--version", "module_version", default="0.1.0", show_default=True, help="Module version.")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.pass_context
def command(
    ctx: click.Context,
    module_name: str | None,
    module_version: str,
    json_output: bool,
    pretty_output: bool,
) -> None:
    """Initialize a new PromptPM module in the current directory."""
    merged_json = json_output or bool(ctx.obj and ctx.obj.get("json_output"))
    merged_pretty = pretty_output or bool(ctx.obj and ctx.obj.get("pretty_output"))
    merged_quiet = bool(ctx.obj and ctx.obj.get("quiet"))
    output_mode = resolve_output_mode(
        json_output=merged_json,
        pretty_output=merged_pretty,
    )

    module_path = os.getcwd()
    effective_name = (module_name or _default_module_name(module_path)).strip()
    try:
        if not effective_name:
            raise ValidationError("module name must be a non-empty string")
        if not isinstance(module_version, str) or not module_version.strip():
            raise ValidationError("module version must be a non-empty string")

        promptpm_yaml = os.path.join(module_path, "promptpm.yaml")
        template_prompt = os.path.join(module_path, "template.prompt")
        tests_dir = os.path.join(module_path, "tests")

        conflicts: list[str] = []
        for target in (promptpm_yaml, template_prompt, tests_dir):
            if os.path.exists(target):
                conflicts.append(os.path.basename(target))
        if conflicts:
            raise ValidationError(
                f"Initialization would overwrite existing paths: {', '.join(sorted(conflicts))}"
            )

        with open(promptpm_yaml, "w", encoding="utf-8") as handle:
            handle.write(_render_promptpm_yaml(name=effective_name, version=module_version.strip()))

        with open(template_prompt, "w", encoding="utf-8") as handle:
            handle.write("Summary:\n{{document}}\n")

        os.makedirs(tests_dir, exist_ok=False)
    except ValidationError as err:
        payload = _validation_error_payload(module_path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(VALIDATION_EXIT_CODE)
    except Exception as err:  # pragma: no cover - defensive path
        payload = _internal_error_payload(module_path, err)
        emit(payload, mode=output_mode, quiet=merged_quiet)
        raise SystemExit(INTERNAL_EXIT_CODE)

    payload = {
        "ok": True,
        "operation": "init",
        "data": {
            "path": os.path.abspath(module_path),
            "created": ["promptpm.yaml", "template.prompt", "tests/"],
            "module": {
                "name": effective_name,
                "version": module_version.strip(),
            },
        },
    }
    emit(payload, mode=output_mode, quiet=merged_quiet)
    raise SystemExit(SUCCESS_EXIT_CODE)
