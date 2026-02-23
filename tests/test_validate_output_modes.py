"""Unit tests for validate command output modes."""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from promptpm.cli import main


VALID_MODULE_YAML = """\
module:
  name: technical-summarizer
  version: "1.0.0"
  description: Summarizes technical documents
prompt:
  template: template.prompt
  placeholders:
    - document
interface:
  intent: Summarize a technical document.
  inputs:
    - name: document
      type: technical_document
      description: Source document text
      required: true
  outputs:
    - type: structured_summary
      description: Concise technical summary
"""


INVALID_MODULE_YAML = """\
module:
  name: technical-summarizer
  version: "1.0.0"
  description: Summarizes technical documents
prompt:
  template: template.prompt
  placeholders:
    - undeclared_input
interface:
  intent: Summarize a technical document.
  inputs:
    - name: document
      type: technical_document
      description: Source document text
      required: true
  outputs:
    - type: structured_summary
      description: Concise technical summary
"""


def test_validate_default_output_success(tmp_path) -> None:
    module_path = tmp_path / "promptpm.yaml"
    module_path.write_text(VALID_MODULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path)])

    expected = (
        f"OK path={json.dumps(os.path.abspath(str(tmp_path)))} "
        f"source={json.dumps(os.path.abspath(str(module_path)))}\n"
    )
    assert result.exit_code == 0
    assert result.output == expected


def test_validate_pretty_output_success(tmp_path) -> None:
    module_path = tmp_path / "promptpm.yaml"
    module_path.write_text(VALID_MODULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["--pretty", "validate", str(tmp_path)])

    expected = (
        "Validation succeeded\n"
        f"path: {os.path.abspath(str(tmp_path))}\n"
        f"source: {os.path.abspath(str(module_path))}\n"
    )
    assert result.exit_code == 0
    assert result.output == expected


def test_validate_default_output_failure(tmp_path) -> None:
    module_path = tmp_path / "promptpm.yaml"
    module_path.write_text(INVALID_MODULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path)])

    expected = (
        'ERROR code="VALIDATION_ERROR" '
        f'path={json.dumps(os.path.abspath(str(tmp_path)))} '
        'message="Undeclared placeholders used in template: undeclared_input" '
        'hint="Fix the module definition and run `promptpm validate` again."\n'
    )
    assert result.exit_code == 1
    assert result.output == expected


def test_validate_json_takes_precedence_over_pretty(tmp_path) -> None:
    module_path = tmp_path / "promptpm.yaml"
    module_path.write_text(VALID_MODULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path), "--json", "--pretty"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["path"] == os.path.abspath(str(tmp_path))
    assert payload["data"]["source"] == os.path.abspath(str(module_path))
