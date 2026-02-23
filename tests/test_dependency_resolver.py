"""Unit tests for dependency resolution."""

from __future__ import annotations

import os

import pytest

from promptpm.core.errors import DependencyError
from promptpm.core.registry import LocalRegistry
from promptpm.core.resolver import DependencyResolver


def _write_module(module_dir, *, name: str, version: str, dependencies=None) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)

    dependency_block = ""
    if dependencies:
        dependency_lines = ["dependencies:"]
        for dependency_name, dependency_version in dependencies:
            dependency_lines.extend(
                [
                    f"  - name: {dependency_name}",
                    f'    version: "{dependency_version}"',
                ]
            )
        dependency_block = "\n" + "\n".join(dependency_lines) + "\n"

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
      description: Concise technical summary{dependency_block}""",
        encoding="utf-8",
    )
    (module_dir / "template.prompt").write_text("Summarize {{document}}", encoding="utf-8")


def test_resolver_selects_highest_matching_version(tmp_path) -> None:
    registry = LocalRegistry(str(tmp_path / "registry"))

    for version in ("1.2.0", "1.5.0", "2.0.0"):
        module_dir = tmp_path / f"dep-lib-{version}"
        _write_module(module_dir, name="dep-lib", version=version)
        registry.install(str(module_dir))

    root_dir = tmp_path / "root"
    _write_module(root_dir, name="root", version="1.0.0", dependencies=[("dep-lib", "^1.2.0")])

    resolver = DependencyResolver(registry)
    resolved = resolver.resolve_for_module(str(root_dir))

    assert [(item.name, item.version) for item in resolved] == [("dep-lib", "1.5.0")]


def test_resolver_is_deterministic_and_topological(tmp_path) -> None:
    registry = LocalRegistry(str(tmp_path / "registry"))

    module_c = tmp_path / "dep-c"
    _write_module(module_c, name="dep-c", version="1.0.0")
    registry.install(str(module_c))

    module_a = tmp_path / "dep-a"
    _write_module(module_a, name="dep-a", version="1.0.0", dependencies=[("dep-c", ">=1.0.0")])
    registry.install(str(module_a))

    module_b = tmp_path / "dep-b"
    _write_module(module_b, name="dep-b", version="1.0.0")
    registry.install(str(module_b))

    root_dir = tmp_path / "root"
    _write_module(
        root_dir,
        name="root",
        version="1.0.0",
        dependencies=[
            ("dep-b", ">=1.0.0"),
            ("dep-a", ">=1.0.0"),
        ],
    )

    resolver = DependencyResolver(registry)
    resolved = resolver.resolve_for_module(str(root_dir))

    assert [(item.name, item.version) for item in resolved] == [
        ("dep-c", "1.0.0"),
        ("dep-a", "1.0.0"),
        ("dep-b", "1.0.0"),
    ]


def test_resolver_rejects_cyclic_dependencies(tmp_path) -> None:
    registry = LocalRegistry(str(tmp_path / "registry"))

    module_a = tmp_path / "dep-a"
    _write_module(module_a, name="dep-a", version="1.0.0", dependencies=[("dep-b", "^1.0.0")])
    registry.install(str(module_a))

    module_b = tmp_path / "dep-b"
    _write_module(module_b, name="dep-b", version="1.0.0", dependencies=[("dep-a", "^1.0.0")])
    registry.install(str(module_b))

    root_dir = tmp_path / "root"
    _write_module(root_dir, name="root", version="1.0.0", dependencies=[("dep-a", "^1.0.0")])

    resolver = DependencyResolver(registry)
    with pytest.raises(DependencyError, match="Cyclic dependency detected"):
        resolver.resolve_for_module(str(root_dir))


def test_resolver_rejects_missing_dependencies(tmp_path) -> None:
    registry = LocalRegistry(str(tmp_path / "registry"))

    root_dir = tmp_path / "root"
    _write_module(root_dir, name="root", version="1.0.0", dependencies=[("dep-a", "^1.0.0")])

    resolver = DependencyResolver(registry)
    with pytest.raises(DependencyError, match="Dependency not found"):
        resolver.resolve_for_module(str(root_dir))


def test_resolver_rejects_invalid_range_expression(tmp_path) -> None:
    registry = LocalRegistry(str(tmp_path / "registry"))

    module_a = tmp_path / "dep-a"
    _write_module(module_a, name="dep-a", version="1.0.0")
    registry.install(str(module_a))

    root_dir = tmp_path / "root"
    _write_module(root_dir, name="root", version="1.0.0", dependencies=[("dep-a", "=>1.0.0")])

    resolver = DependencyResolver(registry)
    with pytest.raises(DependencyError, match="Invalid semantic version"):
        resolver.resolve_for_module(str(root_dir))

