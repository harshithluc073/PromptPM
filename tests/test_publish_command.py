"""Unit tests for `promptpm publish`."""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from promptpm.cli import main
from promptpm.core.registry import IMMUTABILITY_MANIFEST_FILENAME


def _write_module(
    module_dir,
    *,
    name: str,
    version: str,
    test_assertion: dict,
    valid: bool = True,
) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)

    placeholder = "document" if valid else "undeclared_input"
    (module_dir / "promptpm.yaml").write_text(
        f"""\
module:
  name: {name}
  version: "{version}"
  description: Publish test module
prompt:
  template: template.prompt
  placeholders:
    - {placeholder}
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
tests:
  - name: publish-check
    inputs:
      document: hello
    assertions:
      - {next(iter(test_assertion.keys()))}: {json.dumps(next(iter(test_assertion.values())))}
""",
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text("Summary: {{document}}", encoding="utf-8")


def test_publish_success_json(tmp_path) -> None:
    module_dir = tmp_path / "module"
    registry_root = tmp_path / "registry"
    _write_module(
        module_dir,
        name="publish-module",
        version="1.0.0",
        test_assertion={"contains": "hello"},
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "publish", str(module_dir), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["operation"] == "publish"
    assert payload["data"]["identifier"] == "publish-module@1.0.0"
    assert payload["data"]["tests"] == {"total": 1, "passed": 1, "failed": 0}
    assert payload["data"]["registry_path"] == os.path.abspath(str(registry_root))

    manifest_path = (
        registry_root
        / "modules"
        / "publish-module"
        / "1.0.0"
        / IMMUTABILITY_MANIFEST_FILENAME
    )
    assert manifest_path.is_file()


def test_publish_validation_error_exit_code(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        name="publish-module",
        version="1.0.0",
        test_assertion={"contains": "hello"},
        valid=False,
    )

    runner = CliRunner()
    result = runner.invoke(main, ["publish", str(module_dir), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "publish"
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_publish_test_failure_exit_code(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        name="publish-module",
        version="1.0.0",
        test_assertion={"contains": "missing"},
    )

    runner = CliRunner()
    result = runner.invoke(main, ["publish", str(module_dir), "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "publish"
    assert payload["error"]["code"] == "TEST_FAILURE"
    assert payload["data"]["tests"]["failed"] == 1
    assert payload["data"]["failures"][0]["test_name"] == "publish-check"


def test_publish_conflict_exit_code(tmp_path) -> None:
    module_dir = tmp_path / "module"
    registry_root = tmp_path / "registry"
    _write_module(
        module_dir,
        name="publish-module",
        version="1.0.0",
        test_assertion={"contains": "hello"},
    )

    runner = CliRunner()
    first = runner.invoke(
        main,
        ["--registry", str(registry_root), "publish", str(module_dir), "--json"],
    )
    second = runner.invoke(
        main,
        ["--registry", str(registry_root), "publish", str(module_dir), "--json"],
    )

    assert first.exit_code == 0
    assert second.exit_code == 4
    payload = json.loads(second.output)
    assert payload["ok"] is False
    assert payload["operation"] == "publish"
    assert payload["error"]["code"] == "PUBLISH_CONFLICT"
    assert "already exists" in payload["error"]["message"]


def test_publish_rejects_non_local_registry_path(tmp_path) -> None:
    module_dir = tmp_path / "module"
    _write_module(
        module_dir,
        name="publish-module",
        version="1.0.0",
        test_assertion={"contains": "hello"},
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--registry",
            "https://registry.example.com/promptpm",
            "publish",
            str(module_dir),
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "publish"
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"
    assert "local filesystem path" in payload["error"]["message"]

