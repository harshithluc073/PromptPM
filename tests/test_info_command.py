"""Unit tests for `promptpm info`."""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from promptpm.cli import main
from promptpm.core.registry import LocalRegistry


def _write_module(module_dir, *, name: str, version: str, intent: str) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "promptpm.yaml").write_text(
        f"""\
module:
  name: {name}
  version: "{version}"
  description: Info command test module
prompt:
  template: template.prompt
  placeholders:
    - document
interface:
  intent: {intent}
  inputs:
    - name: document
      type: technical_document
      description: Source document text
      required: true
  outputs:
    - type: structured_summary
      description: Concise technical summary
""",
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text("Summary: {{document}}", encoding="utf-8")


def test_info_success_json_single_version(tmp_path) -> None:
    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))
    source = tmp_path / "module"
    _write_module(source, name="alpha-module", version="1.0.0", intent="Summarize alpha")
    registry.install(str(source))

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "info", "alpha-module", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["operation"] == "info"
    assert payload["data"]["registry_path"] == os.path.abspath(str(registry_root))
    assert payload["data"]["name"] == "alpha-module"
    assert payload["data"]["count"] == 1
    version_item = payload["data"]["versions"][0]
    assert version_item["name"] == "alpha-module"
    assert version_item["version"] == "1.0.0"
    assert version_item["metadata"]["description"] == "Info command test module"
    assert version_item["interface"]["intent"] == "Summarize alpha"


def test_info_deterministic_order_multiple_versions(tmp_path) -> None:
    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))

    source_b = tmp_path / "module-b"
    _write_module(source_b, name="alpha-module", version="2.0.0", intent="Summarize v2")
    registry.install(str(source_b))

    source_a = tmp_path / "module-a"
    _write_module(source_a, name="alpha-module", version="1.0.0", intent="Summarize v1")
    registry.install(str(source_a))

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "info", "alpha-module", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [item["version"] for item in payload["data"]["versions"]] == ["1.0.0", "2.0.0"]


def test_info_missing_module_exit_code(tmp_path) -> None:
    registry_root = tmp_path / "registry"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "info", "missing-module", "--json"],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "info"
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"
    assert "Module not found" in payload["error"]["message"]


def test_info_rejects_non_local_registry_path(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--registry",
            "https://registry.example.com/promptpm",
            "info",
            "alpha-module",
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "info"
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"
    assert "local filesystem path" in payload["error"]["message"]

