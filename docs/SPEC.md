# PromptPM Specification

## 1. Purpose

This document defines the formal specification for PromptPM. It describes the core abstractions, rules, and behaviors that govern how prompt modules are defined, validated, tested, versioned, and composed. All implementations of PromptPM must conform to this specification.

The goal of this specification is to provide deterministic, predictable behavior for prompt modules, independent of model providers or runtime environments.

---

## 2. Definitions

### 2.1 Prompt Module

A Prompt Module is the smallest distributable unit in PromptPM. It represents a reusable prompt component with a clearly defined semantic contract.

A Prompt Module consists of:

* Metadata
* A prompt template
* A semantic interface
* Optional dependencies
* Optional unit tests

Prompt Modules are immutable once published.

---

### 2.2 Semantic Interface

A Semantic Interface defines the meaning and guarantees of a Prompt Module beyond raw text. It is used by PromptPM to validate compatibility and safe composition.

A Semantic Interface includes:

* Intent
* Inputs
* Outputs
* Preconditions
* Postconditions

---

### 2.3 Registry

A Registry is a storage mechanism for Prompt Modules. Registries may be local or remote. PromptPM does not require a centralized registry.

---

## 3. Prompt Module Structure

Each Prompt Module MUST contain the following files at its root:

* `promptpm.yaml` (or `promptpm.toml`)
* `template.prompt`

Optional files:

* `tests/`
* `README.md`

---

## 4. Module Metadata

The metadata file defines identity and versioning.

Required fields:

* `name`: globally unique within a registry
* `version`: semantic version
* `description`: short human-readable summary

Optional fields:

* `authors`
* `license`
* `tags`

---

## 5. Prompt Template

The prompt template contains the natural language prompt with placeholders.

Rules:

* Placeholders MUST be explicitly declared in the semantic interface
* Templates MUST be deterministic given the same inputs
* Templates MUST NOT contain runtime logic

---

## 6. Semantic Interface Specification

### 6.1 Intent

The intent describes what the prompt is designed to do in a single, precise statement.

Example:
"Summarize a technical document for a senior software engineer."

---

### 6.2 Inputs

Inputs define required and optional parameters.

Each input MUST specify:

* Name
* Semantic type
* Description
* Required or optional

---

### 6.3 Outputs

Outputs define expected response guarantees.

Each output MUST specify:

* Semantic type
* Structural constraints
* Allowed variance

---

### 6.4 Preconditions

Preconditions define assumptions that must hold true for correct behavior.

Example:

* Input text is in English
* Input length is below a defined limit

---

### 6.5 Postconditions

Postconditions define guarantees provided by the prompt.

Example:

* Output contains no personally identifiable information
* Output follows a specified structure

---

## 7. Semantic Types

Semantic types describe meaning rather than data format.

Examples:

* `technical_document`
* `structured_summary`
* `classification_label`

Semantic types MAY form hierarchies.

---

## 8. Compatibility Rules

Compatibility is determined by semantic interface matching.

Rules:

* Output semantic type MUST be compatible with downstream input type
* Preconditions of downstream module MUST be satisfied by upstream guarantees
* Version constraints MUST be respected

If compatibility cannot be proven, PromptPM MUST reject composition.

---

## 9. Versioning Rules

Prompt Modules use semantic versioning.

Rules:

* Patch versions MUST NOT change semantic behavior
* Minor versions MAY extend behavior but MUST remain backward compatible
* Major versions MAY introduce breaking semantic changes

Published versions are immutable.

---

## 10. Dependencies

Prompt Modules MAY depend on other modules.

Rules:

* Dependencies MUST specify version ranges
* Cyclic dependencies are forbidden
* Dependency resolution MUST be deterministic

---

## 11. Unit Testing

Unit tests define expected behavior.

Tests MAY include:

* Example-based assertions
* Structural validation
* Scoring thresholds

Rules:

* All tests MUST pass before publishing
* Test execution MUST be reproducible

---

## 12. Validation

PromptPM MUST validate:

* Schema correctness
* Semantic interface completeness
* Placeholder consistency
* Dependency resolution

Validation failures MUST provide actionable error messages.

---

## 13. CLI Behavior

The CLI MUST provide commands for:

* Module initialization
* Validation
* Testing
* Installation
* Publishing

CLI output MUST be deterministic and scriptable.

---

## 14. Non-Goals

This specification explicitly excludes:

* UI definitions
* Model-specific optimizations
* Runtime execution engines
* Observability features

---

## 15. Forward Compatibility

The specification is designed to evolve.

Rules:

* New fields MUST be optional
* Existing modules MUST remain valid
* Deprecated features MUST be clearly marked

---

## 16. Compliance

An implementation is compliant with PromptPM if it:

* Follows this specification exactly
* Produces deterministic results
* Enforces all validation and compatibility rules

This specification is the authoritative reference for PromptPM behavior.
