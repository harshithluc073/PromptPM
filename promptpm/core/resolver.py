"""Dependency resolution for PromptPM modules."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cmp_to_key
from typing import Any

from promptpm.core.errors import DependencyError
from promptpm.core.registry import InstalledModule, LocalRegistry
from promptpm.core.schema import load_prompt_module, validate_prompt_module
from promptpm.core.semver import SemVerError, SemanticVersion, compare_versions, parse_version, satisfies_version_range


@dataclass(frozen=True)
class DependencySpec:
    """Normalized dependency declaration."""

    name: str
    version_range: str


@dataclass(frozen=True)
class ResolvedDependency:
    """Resolved dependency record."""

    name: str
    version: str
    path: str


class DependencyResolver:
    """Deterministic local dependency resolver with cycle detection."""

    def __init__(self, registry: LocalRegistry):
        self.registry = registry

    def resolve_for_module(self, module_path: str) -> tuple[ResolvedDependency, ...]:
        """Resolve all transitive dependencies for the given module path."""
        module = load_prompt_module(module_path)
        validate_prompt_module(module)

        resolved: list[ResolvedDependency] = []
        visiting: list[str] = []
        visited: set[str] = set()

        dependencies = _parse_dependencies(module.dependencies, owner=str(module.source_path))
        for dependency in dependencies:
            installed = self._select_installed_version(
                dependency.name,
                dependency.version_range,
                parent=str(module.source_path),
            )
            self._visit(installed, resolved=resolved, visiting=visiting, visited=visited)

        return tuple(resolved)

    def _visit(
        self,
        module: InstalledModule,
        *,
        resolved: list[ResolvedDependency],
        visiting: list[str],
        visited: set[str],
    ) -> None:
        node_id = f"{module.name}@{module.version}"
        if node_id in visited:
            return

        if node_id in visiting:
            cycle = " -> ".join([*visiting, node_id])
            raise DependencyError(f"Cyclic dependency detected: {cycle}")

        visiting.append(node_id)
        try:
            loaded = load_prompt_module(module.path)
            validate_prompt_module(loaded)
            dependencies = _parse_dependencies(loaded.dependencies, owner=node_id)
            for dependency in dependencies:
                installed = self._select_installed_version(
                    dependency.name,
                    dependency.version_range,
                    parent=node_id,
                )
                self._visit(installed, resolved=resolved, visiting=visiting, visited=visited)
        finally:
            visiting.pop()

        visited.add(node_id)
        resolved.append(
            ResolvedDependency(
                name=module.name,
                version=module.version,
                path=os.path.abspath(module.path),
            )
        )

    def _select_installed_version(
        self,
        name: str,
        version_range: str,
        *,
        parent: str,
    ) -> InstalledModule:
        candidates = self.registry.list_by_name(name)
        if not candidates:
            raise DependencyError(
                f"Dependency not found for {parent}: {name} ({version_range})"
            )

        try:
            matching: list[tuple[SemanticVersion, InstalledModule]] = []
            for candidate in candidates:
                semantic_version = parse_version(candidate.version)
                if satisfies_version_range(semantic_version, version_range):
                    matching.append((semantic_version, candidate))
        except SemVerError as err:
            raise DependencyError(
                f"Invalid semantic version while resolving {name} ({version_range}): {err}"
            ) from err

        if not matching:
            raise DependencyError(
                f"No installed versions satisfy dependency for {parent}: "
                f"{name} ({version_range})"
            )

        matching.sort(key=cmp_to_key(_compare_candidate_version))
        return matching[-1][1]


def _parse_dependencies(raw_dependencies: Any, *, owner: str) -> tuple[DependencySpec, ...]:
    if raw_dependencies in (None, []):
        return tuple()

    if not isinstance(raw_dependencies, list):
        raise DependencyError(f"dependencies must be a list in {owner}")

    parsed: list[DependencySpec] = []
    for index, dependency in enumerate(raw_dependencies):
        if not isinstance(dependency, dict):
            raise DependencyError(f"dependency entry at index {index} must be a mapping in {owner}")

        name = dependency.get("name")
        version_range = dependency.get("version")
        if not isinstance(name, str) or not name:
            raise DependencyError(f"dependency.name is required in {owner} at index {index}")
        if not isinstance(version_range, str) or not version_range.strip():
            raise DependencyError(f"dependency.version is required in {owner} at index {index}")

        parsed.append(DependencySpec(name=name, version_range=version_range.strip()))

    parsed.sort(key=lambda entry: (entry.name, entry.version_range))
    return tuple(parsed)


def _compare_candidate_version(
    left: tuple[SemanticVersion, InstalledModule],
    right: tuple[SemanticVersion, InstalledModule],
) -> int:
    semantic_cmp = compare_versions(left[0], right[0])
    if semantic_cmp != 0:
        return semantic_cmp

    # SemVer ignores build metadata in precedence; tie-break on exact string for determinism.
    if left[1].version < right[1].version:
        return -1
    if left[1].version > right[1].version:
        return 1
    return 0

