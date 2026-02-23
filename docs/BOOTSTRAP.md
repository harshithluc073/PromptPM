# PromptPM CLI Bootstrap

This document bootstraps the initial PromptPM repository and CLI skeleton. It defines the repository structure, language choice, and minimal runnable CLI that conforms to the CLI command contract.

---

## Language Choice

**Python** is chosen for the initial implementation.

Reasons:

* Strong YAML and TOML ecosystem
* Fast iteration with Codex
* Excellent CLI tooling
* Easy contributor onboarding
* Cross-platform by default

The architecture is language-agnostic enough to allow a future reimplementation if needed.

---

## Repository Structure

```
promptpm/
├─ promptpm/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ commands/
│  │  ├─ __init__.py
│  │  ├─ init.py
│  │  ├─ validate.py
│  │  ├─ test.py
│  │  ├─ install.py
│  │  ├─ publish.py
│  │  ├─ list.py
│  │  └─ info.py
│  ├─ core/
│  │  ├─ __init__.py
│  │  ├─ schema.py
│  │  ├─ validator.py
│  │  ├─ resolver.py
│  │  ├─ registry.py
│  │  └─ errors.py
│  ├─ utils/
│  │  ├─ __init__.py
│  │  ├─ fs.py
│  │  └─ output.py
│  └─ version.py
├─ tests/
│  └─ test_cli_smoke.py
├─ pyproject.toml
├─ README.md
├─ CONCEPT.md
├─ SPEC.md
├─ AGENTS.md
├─ PROMPT_MODULE_SCHEMA.md
├─ CLI_COMMAND_CONTRACT.md
└─ .gitignore
```

---

## pyproject.toml

```toml
[project]
name = "promptpm"
version = "0.1.0"
description = "Prompt package manager with semantic interfaces and unit tests"
requires-python = ">=3.10"

dependencies = [
  "pyyaml",
  "toml",
  "click"
]

[project.scripts]
promptpm = "promptpm.cli:main"
```

---

## CLI Entrypoint

### promptpm/cli.py

```python
import click
from promptpm.commands import init, validate, test, install, publish, list, info

@click.group()
@click.version_option()
def main():
    """PromptPM CLI"""
    pass

main.add_command(init.command)
main.add_command(validate.command)
main.add_command(test.command)
main.add_command(install.command)
main.add_command(publish.command)
main.add_command(list.command)
main.add_command(info.command)
```

---

## Command Stub Example

### promptpm/commands/validate.py

```python
import click

@click.command()
@click.argument("path", default=".")
def command(path):
    """Validate a prompt module"""
    click.echo("Validation not yet implemented")
```

All commands must follow this pattern.

---

## Core Error Model

### promptpm/core/errors.py

```python
class PromptPMError(Exception):
    code = "INTERNAL_ERROR"

class ValidationError(PromptPMError):
    code = "VALIDATION_ERROR"

class DependencyError(PromptPMError):
    code = "DEPENDENCY_ERROR"
```

---

## Output Rules

All CLI output must be routed through a single utility.

### promptpm/utils/output.py

```python
import json

def emit(data, json_output=False):
    if json_output:
        print(json.dumps(data, indent=2))
    else:
        print(data)
```

---

## Smoke Test

### tests/test_cli_smoke.py

```python
def test_cli_help():
    import subprocess
    result = subprocess.run(["promptpm", "--help"], capture_output=True)
    assert result.returncode == 0
```

---

## Development Rules

* No command implements logic yet
* All behavior must follow SPEC.md
* Core logic goes in core/
* Commands only orchestrate

---

## Next Implementation Order

1. Schema loader and validator
2. `promptpm validate`
3. Semantic compatibility checks
4. Local registry implementation
5. `install` and `publish`
6. Test runner

This bootstrap marks the transition from design to execution.
