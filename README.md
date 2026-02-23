# PromptPM
PromptPM is a CLI-first package manager for prompt modules and agent logic, with deterministic validation, testing, dependency resolution, and publishing.

## 1. Problem statement
Prompt logic is often managed as unstructured application text. In practice, this creates predictable operational issues:

- Prompt changes are hard to version and review as formal artifacts.
- Dependencies between prompts are implicit and fragile.
- Compatibility is checked late, usually at runtime.
- Validation and testing are inconsistent across teams and repositories.
- CI pipelines cannot reliably gate prompt changes with stable machine-readable outputs.

PromptPM addresses this by treating prompts as first-class software units with explicit contracts and deterministic CLI behavior.

## 2. Core idea and how PromptPM works
PromptPM introduces a **prompt module** as the smallest distributable unit. A module contains:

- Module metadata (`name`, `version`, `description`)
- A prompt template file (`template.prompt`)
- A semantic interface (`intent`, `inputs`, `outputs`)
- Optional dependencies with semantic version ranges
- Optional unit tests

PromptPM commands operate directly on module directories:

1. `init` scaffolds a module layout.
2. `validate` checks schema, semantic interface completeness, and placeholder consistency.
3. `test` executes deterministic module tests and reports structured failures.
4. `install` resolves transitive dependencies from a local filesystem registry.
5. `publish` validates, tests, and installs immutably into the local registry.
6. `list` and `info` inspect locally installed modules.

The implementation is local-first and vendor-agnostic. No remote network access is required for registry operations.

## 3. Key features
- Deterministic, scriptable CLI behavior suitable for automation.
- Stable output modes: default, `--json`, and `--pretty`.
- Stable failure signaling via documented exit codes.
- Semantic version parsing, comparison, and range matching.
- Deterministic dependency resolution with cycle detection.
- Local filesystem registry with deterministic module layout.
- Module immutability enforcement for published versions.
- Prompt module test runner with clear, structured failure diagnostics.
- Global CLI flags for registry override, quiet mode, config path, and version output.

## 4. Non-goals
PromptPM intentionally does not provide:

- UI tooling or prompt editors.
- Runtime prompt execution engines.
- Provider-specific integrations or lock-in behavior.
- Telemetry or analytics features.
- Undocumented side effects outside defined CLI and registry behavior.

## 5. Installation
PromptPM is currently used from source in this repository.

### Prerequisites
- Python 3.10+
- `pip`

### Install dependencies
```bash
pip install click pyyaml toml pytest
```

### Run the CLI
```bash
python -m promptpm.cli --help
```

If you expose a console entry point named `promptpm`, command examples below can be used as-is.

## 6. Basic usage examples
All examples assume execution from a module directory unless noted otherwise.

### Initialize a module
```bash
promptpm init --name technical-summarizer --version 0.1.0
```

Creates:
- `promptpm.yaml`
- `template.prompt`
- `tests/`

### Validate a module
```bash
promptpm validate . --json
```

### Run module tests
```bash
promptpm test . --json
```

### Resolve dependencies from local registry
```bash
promptpm install . --registry .promptpm_registry --json
```

### Publish immutably to local registry
```bash
promptpm publish . --registry .promptpm_registry --json
```

## 7. How PromptPM fits into CI/CD
PromptPM is built for non-interactive pipelines:

- Deterministic output for parsers (`--json`)
- Explicit non-zero exit codes on failure
- Local, reproducible registry paths
- No network requirement for current registry operations

Example CI gate:
```bash
promptpm validate . --json
promptpm test . --json
promptpm install . --registry .promptpm_registry --json
```

Example publish stage:
```bash
promptpm publish . --registry .promptpm_registry --json
```

Exit codes (from `CLI_COMMAND_CONTRACT.md`):

- `0`: success
- `1`: validation error
- `2`: test failure
- `3`: dependency resolution error
- `4`: publish conflict
- `5`: internal error

## 8. Project status and stability
- Status: early-stage implementation (`0.1.0`).
- Implemented commands: `init`, `validate`, `test`, `install`, `publish`, `list`, `info`.
- Registry mode: local filesystem only.
- Behavior and constraints are defined by:
  - `SPEC.md`
  - `PROMPT_MODULE_SCHEMA.md`
  - `CLI_COMMAND_CONTRACT.md`

Expect ongoing iteration, but deterministic CLI behavior and explicit contract adherence are core project requirements.

## 9. Contributing
Contributions are welcome.

Before submitting changes:

1. Read `AGENTS.md`, `SPEC.md`, `PROMPT_MODULE_SCHEMA.md`, and `CLI_COMMAND_CONTRACT.md`.
2. Keep behavior deterministic and CLI outputs stable.
3. Add tests for all logic changes.
4. Run the test suite:

```bash
python -m pytest -q
```

5. Keep changes scoped and explicit.

## 10. License
No `LICENSE` file is currently present in this repository. Add an explicit license before redistribution or production adoption.
