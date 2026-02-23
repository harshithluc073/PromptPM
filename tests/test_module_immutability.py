"""Unit tests for published module immutability in local registry."""

from __future__ import annotations

import json

import pytest

from promptpm.core.errors import DependencyError
from promptpm.core.registry import IMMUTABILITY_MANIFEST_FILENAME, LocalRegistry


def _write_module(module_dir, *, name: str, version: str) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "promptpm.yaml").write_text(
        f"""\
module:
  name: {name}
  version: "{version}"
  description: Test module
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


def test_registry_writes_immutability_manifest(tmp_path) -> None:
    source_dir = tmp_path / "module_source"
    _write_module(source_dir, name="immutable-module", version="1.0.0")

    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))
    installed = registry.install(str(source_dir))

    manifest_path = (
        registry_root
        / "modules"
        / "immutable-module"
        / "1.0.0"
        / IMMUTABILITY_MANIFEST_FILENAME
    )
    assert manifest_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["name"] == "immutable-module"
    assert manifest["version"] == "1.0.0"
    assert manifest["algorithm"] == "sha256"
    assert sorted(entry["path"] for entry in manifest["files"]) == [
        "promptpm.yaml",
        "template.prompt",
    ]

    looked_up = registry.lookup("immutable-module", "1.0.0")
    assert looked_up.path == installed.path


def test_registry_detects_tampered_published_module(tmp_path) -> None:
    source_dir = tmp_path / "module_source"
    _write_module(source_dir, name="immutable-module", version="1.0.0")

    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))
    registry.install(str(source_dir))

    installed_template = (
        registry_root
        / "modules"
        / "immutable-module"
        / "1.0.0"
        / "template.prompt"
    )
    installed_template.write_text("tampered", encoding="utf-8")

    with pytest.raises(DependencyError, match="Immutability check failed"):
        registry.lookup("immutable-module", "1.0.0")


def test_registry_detects_missing_immutability_manifest(tmp_path) -> None:
    source_dir = tmp_path / "module_source"
    _write_module(source_dir, name="immutable-module", version="1.0.0")

    registry_root = tmp_path / "registry"
    registry = LocalRegistry(str(registry_root))
    registry.install(str(source_dir))

    manifest_path = (
        registry_root
        / "modules"
        / "immutable-module"
        / "1.0.0"
        / IMMUTABILITY_MANIFEST_FILENAME
    )
    manifest_path.unlink()

    with pytest.raises(DependencyError, match="Immutability manifest missing"):
        registry.lookup("immutable-module", "1.0.0")

