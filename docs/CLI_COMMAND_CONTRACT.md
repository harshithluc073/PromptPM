# PromptPM CLI Command Contract

## Purpose

This document defines the official command-line interface contract for PromptPM. It specifies command names, arguments, flags, expected behavior, and output guarantees. All implementations of the PromptPM CLI MUST conform to this contract.

The CLI is designed to be deterministic, scriptable, and suitable for CI/CD usage.

---

## Global CLI Rules

* Command name: `promptpm`
* All commands MUST support `--help`
* All commands MUST return non-zero exit codes on failure
* Output MUST be stable and machine-readable by default
* Human-friendly output MAY be enabled via `--pretty`
* No interactive prompts unless explicitly defined

---

## Global Flags

* `--config <path>`: Path to PromptPM config file
* `--registry <path|url>`: Override default registry
* `--quiet`: Suppress non-error output
* `--json`: Force JSON output
* `--version`: Print CLI version

---

## Command: init

### Purpose

Initialize a new PromptPM prompt module in the current directory.

### Usage

```
promptpm init [--name <name>] [--version <version>]
```

### Behavior

* Creates `promptpm.yaml`
* Creates `template.prompt`
* Creates `tests/` directory
* Does not overwrite existing files

### Output

* Prints created file list

---

## Command: validate

### Purpose

Validate a prompt module against schema and semantic rules.

### Usage

```
promptpm validate [path]
```

### Behavior

* Validates schema correctness
* Validates semantic interface completeness
* Validates placeholder consistency
* Does not execute prompts

### Output

* Success or detailed validation errors

---

## Command: test

### Purpose

Run unit tests for a prompt module.

### Usage

```
promptpm test [path]
```

### Behavior

* Executes all declared tests
* Fails on first critical error
* Deterministic execution required

### Output

* Test summary
* Per-test pass or fail status

---

## Command: install

### Purpose

Install prompt module dependencies.

### Usage

```
promptpm install [path]
```

### Behavior

* Resolves dependency graph
* Installs modules into local registry
* Ensures deterministic resolution

### Output

* Installed modules and versions

---

## Command: publish

### Purpose

Publish a prompt module to a registry.

### Usage

```
promptpm publish [path]
```

### Behavior

* Validates module
* Runs tests
* Rejects if version already exists
* Publishes immutably

### Output

* Published module identifier

---

## Command: list

### Purpose

List installed prompt modules.

### Usage

```
promptpm list
```

### Behavior

* Reads from local registry

### Output

* Module name, version, source

---

## Command: info

### Purpose

Display detailed information about a prompt module.

### Usage

```
promptpm info <module-name>
```

### Behavior

* Displays metadata and semantic interface

### Output

* Structured module information

---

## Error Handling

* Errors MUST include a machine-readable code
* Errors MUST include a human-readable message
* Errors SHOULD include remediation hints

---

## Exit Codes

* `0`: Success
* `1`: Validation error
* `2`: Test failure
* `3`: Dependency resolution error
* `4`: Publish conflict
* `5`: Internal error

---

## Backward Compatibility

* Commands MUST NOT be removed
* Flags MAY be added
* Behavioral changes require major version bump

---

## Compliance

An implementation is compliant if it:

* Implements all commands defined here
* Respects output and exit code guarantees
* Avoids undocumented side effects

This document is the authoritative reference for PromptPM CLI behavior.
