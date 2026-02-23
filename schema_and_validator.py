"""
Schema loader and validator for PromptPM.

This module implements:
- Loading promptpm.yaml or promptpm.toml
- Static schema validation
- Semantic interface validation

It is the foundation for `promptpm validate`.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import yaml
import toml

from promptpm.core.errors import ValidationError


REQUIRED_TOP_LEVEL_FIELDS = {"module", "prompt", "interface"}


class PromptModule:
    def __init__(self, raw: Dict[str, Any], source_path: str):
        self.raw = raw
        self.source_path = source_path
        self.module = raw.get("module")
        self.prompt = raw.get("prompt")
        self.interface = raw.get("interface")
        self.dependencies = raw.get("dependencies", [])
        self.tests = raw.get("tests", [])


# -----------------------------
# Loader
# -----------------------------

def load_prompt_module(path: str) -> PromptModule:
    """
    Load a PromptPM module definition from disk.

    Args:
        path: Directory containing promptpm.yaml or promptpm.toml

    Returns:
        PromptModule

    Raises:
        ValidationError
    """
    yaml_path = os.path.join(path, "promptpm.yaml")
    toml_path = os.path.join(path, "promptpm.toml")

    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        source = yaml_path
    elif os.path.exists(toml_path):
        with open(toml_path, "r", encoding="utf-8") as f:
            raw = toml.load(f)
        source = toml_path
    else:
        raise ValidationError(
            "Missing promptpm.yaml or promptpm.toml",
        )

    if not isinstance(raw, dict):
        raise ValidationError("Module definition must be a mapping")

    return PromptModule(raw=raw, source_path=source)


# -----------------------------
# Validator
# -----------------------------

def validate_prompt_module(module: PromptModule) -> None:
    """
    Validate a PromptModule against the PromptPM specification.

    Raises:
        ValidationError
    """
    _validate_top_level(module)
    _validate_module_metadata(module.module)
    _validate_prompt_block(module.prompt, module.interface)
    _validate_interface(module.interface)


# -----------------------------
# Validation helpers
# -----------------------------

def _validate_top_level(module: PromptModule) -> None:
    missing = REQUIRED_TOP_LEVEL_FIELDS - module.raw.keys()
    if missing:
        raise ValidationError(
            f"Missing required top-level fields: {', '.join(sorted(missing))}"
        )


def _validate_module_metadata(meta: Dict[str, Any]) -> None:
    if not isinstance(meta, dict):
        raise ValidationError("module must be a mapping")

    for field in ("name", "version", "description"):
        if field not in meta:
            raise ValidationError(f"module.{field} is required")

    if not isinstance(meta["name"], str) or not meta["name"]:
        raise ValidationError("module.name must be a non-empty string")

    if not isinstance(meta["version"], str):
        raise ValidationError("module.version must be a string")


def _validate_prompt_block(prompt: Dict[str, Any], interface: Dict[str, Any]) -> None:
    if not isinstance(prompt, dict):
        raise ValidationError("prompt must be a mapping")

    if "template" not in prompt:
        raise ValidationError("prompt.template is required")

    if "placeholders" not in prompt or not isinstance(prompt["placeholders"], list):
        raise ValidationError("prompt.placeholders must be a list")

    declared_inputs = {
        inp.get("name") for inp in interface.get("inputs", []) if isinstance(inp, dict)
    }

    undeclared = set(prompt["placeholders"]) - declared_inputs
    if undeclared:
        raise ValidationError(
            f"Undeclared placeholders used in template: {', '.join(sorted(undeclared))}"
        )


def _validate_interface(interface: Dict[str, Any]) -> None:
    if not isinstance(interface, dict):
        raise ValidationError("interface must be a mapping")

    if "intent" not in interface:
        raise ValidationError("interface.intent is required")

    if "inputs" not in interface or not isinstance(interface["inputs"], list):
        raise ValidationError("interface.inputs must be a list")

    if "outputs" not in interface or not isinstance(interface["outputs"], list):
        raise ValidationError("interface.outputs must be a list")

    for inp in interface["inputs"]:
        _validate_interface_input(inp)

    for out in interface["outputs"]:
        _validate_interface_output(out)


def _validate_interface_input(inp: Dict[str, Any]) -> None:
    if not isinstance(inp, dict):
        raise ValidationError("interface.inputs entries must be mappings")

    for field in ("name", "type", "description", "required"):
        if field not in inp:
            raise ValidationError(f"interface.inputs.{field} is required")


def _validate_interface_output(out: Dict[str, Any]) -> None:
    if not isinstance(out, dict):
        raise ValidationError("interface.outputs entries must be mappings")

    for field in ("type", "description"):
        if field not in out:
            raise ValidationError(f"interface.outputs.{field} is required")
