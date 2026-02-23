"""Unit tests for `promptpm list`."""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from promptpm.cli import main
from promptpm.core.registry import LocalRegistry


def _write_module(module_dir, *, name: str, version: str) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "promptpm.yaml").write_text(
        f"""\
module:
  name: {name}
  version: "{version}"
  description: List command test module
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
""",
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text("Summary: {{document}}", encoding="utf-8")


def test_list_empty_registry_json(tmp_path) -> None:
    registry_root = tmp_path / "registry"

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "list", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["operation"] == "list"
    assert payload["data"]["registry_path"] == os.path.abspath(str(registry_root))
    assert payload["data"]["count"] == 0
    assert payload["data"]["modules"] == []


def test_list_deterministic_order_and_structure(tmp_path) -> None:
    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))

    for name, version in [
        ("beta-module", "1.0.0"),
        ("alpha-module", "2.0.0"),
        ("alpha-module", "1.0.0"),
    ]:
        source = tmp_path / f"{name}-{version}"
        _write_module(source, name=name, version=version)
        registry.install(str(source))

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "list", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["operation"] == "list"
    assert payload["data"]["count"] == 3
    assert payload["data"]["modules"] == [
        {
            "name": "alpha-module",
            "version": "1.0.0",
            "source": os.path.abspath(str(registry_root / "modules" / "alpha-module" / "1.0.0")),
        },
        {
            "name": "alpha-module",
            "version": "2.0.0",
            "source": os.path.abspath(str(registry_root / "modules" / "alpha-module" / "2.0.0")),
        },
        {
            "name": "beta-module",
            "version": "1.0.0",
            "source": os.path.abspath(str(registry_root / "modules" / "beta-module" / "1.0.0")),
        },
    ]


def test_list_rejects_non_local_registry_path(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--registry",
            "https://registry.example.com/promptpm",
            "list",
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "list"
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"
    assert "local filesystem path" in payload["error"]["message"]

