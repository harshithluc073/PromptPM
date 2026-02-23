"""Unit tests for the core prompt module test runner."""

from __future__ import annotations

import pytest
import yaml

from promptpm.core.errors import ValidationError
from promptpm.core.test_runner import run_prompt_module_tests


def _write_module(module_dir, *, template: str, tests: list[dict]) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    spec = {
        "module": {
            "name": "runner-test-module",
            "version": "1.0.0",
            "description": "Runner test module",
        },
        "prompt": {
            "template": "template.prompt",
            "placeholders": ["document", "payload"],
        },
        "interface": {
            "intent": "Test module",
            "inputs": [
                {
                    "name": "document",
                    "type": "technical_document",
                    "description": "Input document",
                    "required": True,
                },
                {
                    "name": "payload",
                    "type": "structured_summary",
                    "description": "Structured payload",
                    "required": False,
                },
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


def test_runner_executes_in_deterministic_order(tmp_path) -> None:
    module_dir = tmp_path / "module"
    (module_dir / "doc.txt").parent.mkdir(parents=True, exist_ok=True)
    (module_dir / "doc.txt").write_text("from-file", encoding="utf-8")

    _write_module(
        module_dir,
        template="Summary: {{document}}",
        tests=[
            {
                "name": "z-test",
                "inputs": {"document": "doc.txt"},
                "assertions": [{"contains": "from-file"}],
            },
            {
                "name": "a-test",
                "inputs": {"document": "inline"},
                "assertions": [
                    {"contains": "inline"},
                    {"excludes": "forbidden"},
                    {"max_length": 40},
                ],
            },
        ],
    )

    result = run_prompt_module_tests(str(module_dir))

    assert result.total == 2
    assert result.passed == 2
    assert result.failed == 0
    assert [case.name for case in result.results] == ["a-test", "z-test"]


def test_runner_reports_assertion_failures_with_diagnostics(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        template="Summary: {{document}}",
        tests=[
            {
                "name": "fails-contains",
                "inputs": {"document": "hello"},
                "assertions": [{"contains": "missing"}],
            }
        ],
    )

    result = run_prompt_module_tests(str(module_dir))

    assert result.total == 1
    assert result.passed == 0
    assert result.failed == 1
    failure = result.results[0].failures[0]
    assert failure.test_name == "fails-contains"
    assert failure.assertion_type == "contains"
    assert "Expected output to contain" in failure.message
    assert failure.expected == "missing"


def test_runner_supports_structure_assertions(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        template="{{payload}}",
        tests=[
            {
                "name": "structure-pass",
                "inputs": {"payload": '{"name":"x","value":1}'},
                "assertions": [
                    {
                        "structure": {
                            "type": "json_object",
                            "required_keys": ["name", "value"],
                        }
                    }
                ],
            }
        ],
    )

    result = run_prompt_module_tests(str(module_dir))

    assert result.failed == 0
    assert result.passed == 1


def test_runner_rejects_unsupported_assertion_type(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        template="Summary: {{document}}",
        tests=[
            {
                "name": "invalid-assertion",
                "inputs": {"document": "hello"},
                "assertions": [{"unknown_assertion": "value"}],
            }
        ],
    )

    with pytest.raises(ValidationError, match="Unsupported assertion type"):
        run_prompt_module_tests(str(module_dir))
