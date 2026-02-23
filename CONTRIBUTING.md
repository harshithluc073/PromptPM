# Contributing to PromptPM

Thank you for contributing. PromptPM is an infrastructure project, and contributions are reviewed for correctness, determinism, and long-term maintainability.

SPEC-first development is required:

- `SPEC.md` defines project behavior and is the primary source of truth.
- `CLI_COMMAND_CONTRACT.md` defines command behavior, flags, exit codes, and output guarantees.
- `PROMPT_MODULE_SCHEMA.md` defines module schema and validation expectations.
- `AGENTS.md` defines requirements for autonomous and AI contributors.

If implementation and specification differ, update the spec first or align code to the current spec. Do not ship undocumented behavior.

## 1. Development environment setup

### Prerequisites
- Python 3.10 or newer
- `pip`

### Setup
```bash
python -m venv .venv
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:
```bash
pip install click pyyaml toml pytest
```

Run tests:
```bash
python -m pytest -q
```

Run CLI help:
```bash
python -m promptpm.cli --help
```

## 2. Project structure overview

Core repository layout:

- `promptpm/cli.py`: CLI entrypoint and global options.
- `promptpm/commands/`: command handlers (`init`, `validate`, `test`, `install`, `publish`, `list`, `info`).
- `promptpm/core/`: domain logic (schema wrapper, semver, resolver, registry, test runner, errors).
- `promptpm/utils/`: shared utilities (including deterministic output formatting).
- `schema_and_validator.py`: schema loading and validation implementation.
- `tests/`: unit and contract-oriented CLI tests.
- `SPEC.md`: behavioral specification.
- `CLI_COMMAND_CONTRACT.md`: CLI behavior contract.
- `PROMPT_MODULE_SCHEMA.md`: prompt module schema contract.
- `AGENTS.md`: AI contributor governance and constraints.

## 3. Rules for adding or changing behavior

1. Start with specification.
2. Confirm whether behavior is already defined in `SPEC.md` and relevant contract documents.
3. If behavior is undefined, propose and land specification changes before implementation.
4. Keep behavior deterministic and scriptable.
5. Keep commands non-interactive unless explicitly specified.
6. Do not introduce undocumented side effects, hidden config paths, or implicit network behavior.
7. Treat prompt content as untrusted input; do not execute prompts.
8. Use explicit errors and documented exit codes.
9. Preserve backward compatibility unless a spec-directed breaking change is accepted.
10. For AI-generated changes, comply with `AGENTS.md`.

## 4. Testing requirements

All behavior changes must include tests.

Required standards:

- Add unit tests for new logic.
- Add or update CLI tests when command behavior, output, error codes, or exit codes change.
- Keep tests deterministic (fixed ordering, no timing/race assumptions, no network dependency).
- Validate both success and failure paths for command changes.
- Ensure tests align with `CLI_COMMAND_CONTRACT.md` and `SPEC.md`.

Minimum local verification before opening a PR:
```bash
python -m pytest -q
```

## 5. Commit and PR guidelines

### Commits
- Keep each commit scoped to one logical change.
- Do not mix unrelated refactors with behavior changes.
- Write clear, imperative commit messages.
- Keep diffs reviewable and traceable to specification requirements.

### Pull requests
- Explain the problem and why the change is needed.
- Reference relevant sections of `SPEC.md`, `CLI_COMMAND_CONTRACT.md`, and/or `PROMPT_MODULE_SCHEMA.md`.
- Describe behavioral impact clearly, including output/exit code effects.
- Include tests for every functional change.
- Do not include undocumented behavior.

PRs that change behavior without specification alignment should not be merged.

## 6. How to report bugs

Open an issue with:

1. Clear summary and impact.
2. Reproduction steps (exact commands and inputs).
3. Expected behavior (with spec reference).
4. Actual behavior (including output and exit code).
5. Environment details (OS, Python version, PromptPM revision).
6. Minimal module example if relevant.

If possible, include a failing test case proposal.

## 7. How to propose new features

Use a spec-first proposal process:

1. Open an issue describing the problem, scope, and non-goals.
2. Propose exact behavior changes to `SPEC.md` and related contracts.
3. Define CLI interface impact (flags, output shape, exit codes, error codes).
4. Address determinism, safety, compatibility, and migration considerations.
5. Reach maintainer agreement before implementation.

Feature PRs should include:
- Specification updates
- Implementation
- Tests
- Documentation updates

No new behavior should be merged if it is not documented in the project’s authoritative specifications.
