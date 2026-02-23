"""Unit tests for `promptpm test` command."""

from __future__ import annotations

import json
import os

import yaml
from click.testing import CliRunner

from promptpm.cli import main


def _write_module(module_dir, *, template: str, tests: list[dict]) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    spec = {
        "module": {
            "name": "command-test-module",
            "version": "1.0.0",
            "description": "Command test module",
        },
        "prompt": {
            "template": "template.prompt",
            "placeholders": ["document"],
        },
        "interface": {
            "intent": "Test module",
            "inputs": [
                {
                    "name": "document",
                    "type": "technical_document",
                    "description": "Input document",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "type": "structured_summary",
                    "description": "Summary output",
                }
            ],
        },
        "tests": tests,
    }
    (module_dir / "promptpm.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False),
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text(template, encoding="utf-8")


def test_test_command_success_json(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        template="Summary: {{document}}",
        tests=[
            {
                "name": "case-pass",
                "inputs": {"document": "hello"},
                "assertions": [{"contains": "hello"}],
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(main, ["test", str(module_dir), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["operation"] == "test"
    assert payload["data"]["module_path"] == os.path.abspath(str(module_dir))
    assert payload["data"]["total"] == 1
    assert payload["data"]["passed"] == 1
    assert payload["data"]["failed"] == 0
    assert payload["data"]["results"] == [
        {"name": "case-pass", "status": "passed", "failure_count": 0}
    ]


def test_test_command_failure_exit_code_and_diagnostics(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        template="Summary: {{document}}",
        tests=[
            {
                "name": "case-fail",
                "inputs": {"document": "hello"},
                "assertions": [{"contains": "missing"}],
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(main, ["test", str(module_dir), "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "test"
    assert payload["error"]["code"] == "TEST_FAILURE"
    assert payload["data"]["failed"] == 1
    assert payload["data"]["failures"][0]["test_name"] == "case-fail"
    assert payload["data"]["failures"][0]["assertion_type"] == "contains"


def test_test_command_validation_error_exit_code(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        template="Summary: {{document}}",
        tests=[
            {
                "name": "bad-test",
                "inputs": {"document": "hello"},
                "assertions": [{"unsupported": "x"}],
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(main, ["test", str(module_dir), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "test"
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported assertion type" in payload["error"]["message"]

