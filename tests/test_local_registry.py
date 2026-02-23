"""Unit tests for local filesystem registry behavior."""

from __future__ import annotations

import os

import pytest

from promptpm.core.errors import DependencyError
from promptpm.core.registry import LocalRegistry


def _write_module(module_dir, *, name: str, version: str) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "promptpm.yaml").write_text(
        f"""\
module:
  name: {name}
  version: "{version}"
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
""",
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text("Summarize {{document}}", encoding="utf-8")


def test_registry_install_and_lookup(tmp_path) -> None:
    source_dir = tmp_path / "module_source"
    _write_module(source_dir, name="technical-summarizer", version="1.2.3")

    nested_dir = source_dir / "tests"
    nested_dir.mkdir()
    (nested_dir / "sample.txt").write_text("example", encoding="utf-8")

    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))

    installed = registry.install(str(source_dir))
    looked_up = registry.lookup("technical-summarizer", "1.2.3")

    expected_path = os.path.abspath(
        str(registry_root / "modules" / "technical-summarizer" / "1.2.3")
    )
    assert installed.path == expected_path
    assert looked_up.path == expected_path
    assert (registry_root / "modules" / "technical-summarizer" / "1.2.3" / "promptpm.yaml").is_file()
    assert (registry_root / "modules" / "technical-summarizer" / "1.2.3" / "tests" / "sample.txt").is_file()


def test_registry_install_rejects_duplicate_version(tmp_path) -> None:
    source_dir = tmp_path / "module_source"
    _write_module(source_dir, name="technical-summarizer", version="1.0.0")

    registry = LocalRegistry(str(tmp_path / "registry"))
    registry.install(str(source_dir))

    with pytest.raises(DependencyError, match="already installed"):
        registry.install(str(source_dir))


def test_registry_lookup_missing_module(tmp_path) -> None:
    registry = LocalRegistry(str(tmp_path / "registry"))

    with pytest.raises(DependencyError, match="Module not found"):
        registry.lookup("technical-summarizer", "9.9.9")


def test_registry_install_rejects_unsafe_name_segment(tmp_path) -> None:
    source_dir = tmp_path / "module_source"
    _write_module(source_dir, name="../escape", version="1.0.0")

    registry = LocalRegistry(str(tmp_path / "registry"))

    with pytest.raises(DependencyError, match="must not include path separators"):
        registry.install(str(source_dir))

