"""Unit tests for `promptpm validate`."""

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


def test_validate_success_json(tmp_path) -> None:
    module_path = tmp_path / "promptpm.yaml"
    module_path.write_text(VALID_MODULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert payload["ok"] is True
    assert payload["data"]["path"] == os.path.abspath(str(tmp_path))
    assert payload["data"]["source"] == os.path.abspath(str(module_path))


def test_validate_failure_json(tmp_path) -> None:
    module_path = tmp_path / "promptpm.yaml"
    module_path.write_text(INVALID_MODULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "Undeclared placeholders used in template" in payload["error"]["message"]
    assert payload["error"]["path"] == os.path.abspath(str(tmp_path))

