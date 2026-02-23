"""Local filesystem-backed registry for PromptPM modules."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from promptpm.core.errors import DependencyError
from promptpm.core.schema import load_prompt_module, validate_prompt_module

MODULES_DIRNAME = "modules"
IMMUTABILITY_MANIFEST_FILENAME = ".promptpm_immutable.json"
_SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


@dataclass(frozen=True)
class InstalledModule:
    """Represents a module installed in the local registry."""

    name: str
    version: str
    path: str


class LocalRegistry:
    """Local PromptPM registry with deterministic on-disk layout."""

    def __init__(self, root_path: str):
        self.root_path = os.path.abspath(root_path)
        self.modules_root = os.path.join(self.root_path, MODULES_DIRNAME)

    def install(self, module_path: str) -> InstalledModule:
        """
        Install a PromptPM module into the local registry.

        The module is validated before install and then copied to:
        <registry-root>/modules/<name>/<version>
        """
        module = load_prompt_module(module_path)
        validate_prompt_module(module)

        name = _validate_segment(module.module["name"], "module.name")
        version = _validate_segment(module.module["version"], "module.version")
        destination = self._module_directory(name, version)

        if os.path.exists(destination):
            raise DependencyError(
                f"Module already installed: {name}@{version}. "
                "Published versions are immutable and cannot be overwritten."
            )

        source_dir = os.path.abspath(module_path)
        if not os.path.isdir(source_dir):
            raise DependencyError(f"Module path must be a directory: {source_dir}")

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        temp_dir = f"{destination}.tmp"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        try:
            self._copy_tree_deterministic(source_dir, temp_dir)
            self._write_immutability_manifest(temp_dir, name=name, version=version)
            os.replace(temp_dir, destination)
        except Exception as err:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)
            raise DependencyError(f"Failed to install module {name}@{version}: {err}") from err

        return InstalledModule(name=name, version=version, path=destination)

    def lookup(self, name: str, version: str) -> InstalledModule:
        """Lookup an installed module by exact name and version."""
        safe_name = _validate_segment(name, "name")
        safe_version = _validate_segment(version, "version")
        path = self._module_directory(safe_name, safe_version)

        if not os.path.isdir(path):
            raise DependencyError(f"Module not found: {safe_name}@{safe_version}")

        self._verify_immutability(path, name=safe_name, version=safe_version)
        return InstalledModule(name=safe_name, version=safe_version, path=path)

    def list_by_name(self, name: str) -> tuple[InstalledModule, ...]:
        """List all installed versions for a module name in deterministic order."""
        safe_name = _validate_segment(name, "name")
        module_dir = os.path.join(self.modules_root, safe_name)
        if not os.path.isdir(module_dir):
            return tuple()

        installed: list[InstalledModule] = []
        for version in sorted(os.listdir(module_dir)):
            path = os.path.join(module_dir, version)
            if not os.path.isdir(path):
                continue
            safe_version = _validate_segment(version, "version")
            self._verify_immutability(path, name=safe_name, version=safe_version)
            installed.append(InstalledModule(name=safe_name, version=safe_version, path=path))
        return tuple(installed)

    def list_installed(self) -> tuple[InstalledModule, ...]:
        """List all installed modules in deterministic order."""
        if not os.path.isdir(self.modules_root):
            return tuple()

        installed: list[InstalledModule] = []
        for name in sorted(os.listdir(self.modules_root)):
            module_dir = os.path.join(self.modules_root, name)
            if not os.path.isdir(module_dir):
                continue
            safe_name = _validate_segment(name, "name")
            installed.extend(self.list_by_name(safe_name))
        return tuple(installed)

    def has_version(self, name: str, version: str) -> bool:
        """Return True if module name/version already exists in the registry."""
        safe_name = _validate_segment(name, "name")
        safe_version = _validate_segment(version, "version")
        return os.path.isdir(self._module_directory(safe_name, safe_version))

    def _module_directory(self, name: str, version: str) -> str:
        return os.path.join(self.modules_root, name, version)

    def _copy_tree_deterministic(self, source_dir: str, destination_dir: str) -> None:
        source_root = Path(source_dir).resolve()
        destination_root = Path(destination_dir)
        destination_root.mkdir(parents=True, exist_ok=False)

        for file_path in self._iter_files_sorted(source_root):
            relative_path = file_path.relative_to(source_root)
            target_path = destination_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target_path)

    def _iter_files_sorted(self, root: Path) -> Iterator[Path]:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            current_dir = Path(dirpath)

            for dirname in list(dirnames):
                full_dir = current_dir / dirname
                if full_dir.is_symlink():
                    raise DependencyError(
                        f"Symlinks are not allowed in registry installs: {full_dir}"
                    )

            dirnames[:] = sorted(dirnames)

            for filename in sorted(filenames):
                full_file = current_dir / filename
                if full_file.is_symlink():
                    raise DependencyError(
                        f"Symlinks are not allowed in registry installs: {full_file}"
                    )
                if not full_file.is_file():
                    continue
                yield full_file

    def _write_immutability_manifest(self, root_dir: str, *, name: str, version: str) -> None:
        root_path = Path(root_dir).resolve()
        files: list[dict[str, str]] = []
        for full_file in self._iter_files_sorted(root_path):
            relative = full_file.relative_to(root_path).as_posix()
            if relative == IMMUTABILITY_MANIFEST_FILENAME:
                continue
            files.append(
                {
                    "path": relative,
                    "sha256": _sha256_file(full_file),
                }
            )

        manifest_path = os.path.join(root_dir, IMMUTABILITY_MANIFEST_FILENAME)
        manifest_payload = {
            "name": name,
            "version": version,
            "algorithm": "sha256",
            "files": files,
        }
        with open(manifest_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")

    def _verify_immutability(self, root_dir: str, *, name: str, version: str) -> None:
        manifest_path = os.path.join(root_dir, IMMUTABILITY_MANIFEST_FILENAME)
        if not os.path.isfile(manifest_path):
            raise DependencyError(
                f"Immutability manifest missing for published module: {name}@{version}"
            )

        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest_payload = json.load(handle)
        except Exception as err:
            raise DependencyError(
                f"Invalid immutability manifest for {name}@{version}: {err}"
            ) from err

        if not isinstance(manifest_payload, dict):
            raise DependencyError(f"Invalid immutability manifest for {name}@{version}: root must be a mapping")

        manifest_name = manifest_payload.get("name")
        manifest_version = manifest_payload.get("version")
        algorithm = manifest_payload.get("algorithm")
        files = manifest_payload.get("files")

        if manifest_name != name or manifest_version != version:
            raise DependencyError(
                f"Immutability manifest identity mismatch for {name}@{version}"
            )
        if algorithm != "sha256":
            raise DependencyError(
                f"Unsupported immutability hash algorithm for {name}@{version}: {algorithm!r}"
            )
        if not isinstance(files, list):
            raise DependencyError(f"Invalid immutability manifest for {name}@{version}: files must be a list")

        expected_hashes: dict[str, str] = {}
        for entry in files:
            if not isinstance(entry, dict):
                raise DependencyError(
                    f"Invalid immutability manifest for {name}@{version}: file entries must be mappings"
                )

            rel_path = entry.get("path")
            sha256 = entry.get("sha256")
            if not isinstance(rel_path, str) or not rel_path:
                raise DependencyError(
                    f"Invalid immutability manifest for {name}@{version}: file path must be a non-empty string"
                )
            if not isinstance(sha256, str) or len(sha256) != 64:
                raise DependencyError(
                    f"Invalid immutability manifest for {name}@{version}: sha256 must be a 64-char string"
                )
            if rel_path in expected_hashes:
                raise DependencyError(
                    f"Invalid immutability manifest for {name}@{version}: duplicate path {rel_path!r}"
                )
            expected_hashes[rel_path] = sha256

        root_path = Path(root_dir).resolve()
        actual_hashes: dict[str, str] = {}
        for full_file in self._iter_files_sorted(root_path):
            relative = full_file.relative_to(root_path).as_posix()
            if relative == IMMUTABILITY_MANIFEST_FILENAME:
                continue
            actual_hashes[relative] = _sha256_file(full_file)

        missing_files = sorted(set(expected_hashes) - set(actual_hashes))
        extra_files = sorted(set(actual_hashes) - set(expected_hashes))
        changed_files = sorted(
            path
            for path in set(expected_hashes) & set(actual_hashes)
            if expected_hashes[path] != actual_hashes[path]
        )

        if missing_files or extra_files or changed_files:
            details: list[str] = []
            if missing_files:
                details.append(f"missing files: {', '.join(missing_files)}")
            if extra_files:
                details.append(f"extra files: {', '.join(extra_files)}")
            if changed_files:
                details.append(f"changed files: {', '.join(changed_files)}")
            raise DependencyError(
                f"Immutability check failed for published module {name}@{version}: "
                + "; ".join(details)
            )


def _validate_segment(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise DependencyError(f"{field} must be a non-empty string")

    if value in {".", ".."}:
        raise DependencyError(f"{field} contains invalid path segment: {value!r}")

    if "/" in value or "\\" in value:
        raise DependencyError(f"{field} must not include path separators: {value!r}")

    if not _SAFE_SEGMENT_PATTERN.match(value):
        raise DependencyError(
            f"{field} contains unsupported characters: {value!r}. "
            "Use letters, numbers, '.', '_', '+', or '-'."
        )

    return value


def _sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
