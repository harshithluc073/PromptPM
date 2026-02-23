"""Unit tests for `promptpm install`."""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from promptpm.cli import main
from promptpm.core.registry import LocalRegistry


def _write_module(module_dir, *, name: str, version: str, dependencies=None, valid: bool = True) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)

    placeholder = "document" if valid else "undeclared_input"
    dependency_block = ""
    if dependencies:
        lines = ["dependencies:"]
        for dependency_name, dependency_version in dependencies:
            lines.extend(
                [
                    f"  - name: {dependency_name}",
                    f'    version: "{dependency_version}"',
                ]
            )
        dependency_block = "\n" + "\n".join(lines) + "\n"

    (module_dir / "promptpm.yaml").write_text(
        f"""\
module:
  name: {name}
  version: "{version}"
  description: Test module
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
      description: Concise technical summary{dependency_block}""",
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text("Summarize {{document}}", encoding="utf-8")


def test_install_success_json_output(tmp_path) -> None:
    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))

    dep_c = tmp_path / "dep-c"
    _write_module(dep_c, name="dep-c", version="1.0.0")
    registry.install(str(dep_c))

    dep_a = tmp_path / "dep-a"
    _write_module(dep_a, name="dep-a", version="1.0.0", dependencies=[("dep-c", ">=1.0.0")])
    registry.install(str(dep_a))

    dep_b = tmp_path / "dep-b"
    _write_module(dep_b, name="dep-b", version="1.0.0")
    registry.install(str(dep_b))

    root = tmp_path / "root"
    _write_module(
        root,
        name="root",
        version="1.0.0",
        dependencies=[("dep-b", ">=1.0.0"), ("dep-a", ">=1.0.0")],
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", str(registry_root), "install", str(root), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert payload["ok"] is True
    assert payload["operation"] == "install"
    assert payload["data"]["module_path"] == os.path.abspath(str(root))
    assert payload["data"]["registry_path"] == os.path.abspath(str(registry_root))
    assert payload["data"]["count"] == 3
    assert [(entry["name"], entry["version"]) for entry in payload["data"]["installed"]] == [
        ("dep-c", "1.0.0"),
        ("dep-a", "1.0.0"),
        ("dep-b", "1.0.0"),
    ]


def test_install_dependency_resolution_error_exit_code(tmp_path) -> None:
    root = tmp_path / "root"
    _write_module(root, name="root", version="1.0.0", dependencies=[("missing-dep", "^1.0.0")])

    runner = CliRunner()
    result = runner.invoke(main, ["install", str(root), "--json"])

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "install"
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"
    assert "Dependency not found" in payload["error"]["message"]


def test_install_validation_error_exit_code(tmp_path) -> None:
    root = tmp_path / "root"
    _write_module(root, name="root", version="1.0.0", valid=False)

    runner = CliRunner()
    result = runner.invoke(main, ["install", str(root), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["operation"] == "install"
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "Undeclared placeholders used in template" in payload["error"]["message"]


def test_install_rejects_non_local_registry_path(tmp_path) -> None:
    root = tmp_path / "root"
    _write_module(root, name="root", version="1.0.0")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--registry", "https://registry.example.com/promptpm", "install", str(root), "--json"],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"
    assert "local filesystem path" in payload["error"]["message"]

