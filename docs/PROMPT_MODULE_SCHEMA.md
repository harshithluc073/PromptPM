# PromptPM Prompt Module Schema

## Overview

This document defines the canonical schema for a PromptPM Prompt Module. The schema describes how prompt modules are declared, validated, and interpreted by the PromptPM CLI. All prompt modules MUST conform to this schema to be considered valid.

The schema is intentionally minimal, explicit, and deterministic. It is designed to support static validation, semantic compatibility checks, and safe composition.

---

## Schema Format

PromptPM supports YAML and TOML formats for module declaration. The logical schema is identical for both formats.

The canonical filename is:

* `promptpm.yaml` or `promptpm.toml`

---

## Top-Level Fields

### Required Fields

* `module`
* `prompt`
* `interface`

### Optional Fields

* `dependencies`
* `tests`

---

## module

Defines the identity and metadata of the prompt module.

Fields:

* `name` (string, required)

  * Unique identifier within a registry
* `version` (string, required)

  * Semantic version
* `description` (string, required)

  * Short summary of module intent
* `license` (string, optional)
* `authors` (list of strings, optional)
* `tags` (list of strings, optional)

Example:

```yaml
module:
  name: technical-summarizer
  version: 1.0.0
  description: Summarizes technical documents for software engineers
  license: Apache-2.0
  tags: [summarization, technical]
```

---

## prompt

Defines the prompt template used by the module.

Fields:

* `template` (string, required)

  * Path to the prompt template file
* `placeholders` (list of strings, required)

  * All placeholders used in the template

Rules:

* All placeholders MUST be declared
* Undeclared placeholders are invalid
* Templates MUST be static text

Example:

```yaml
prompt:
  template: template.prompt
  placeholders:
    - document
    - audience
```

---

## interface

Defines the semantic contract of the prompt module.

### interface.intent

* `intent` (string, required)

  * Single-sentence description of what the prompt does

---

### interface.inputs

Defines semantic inputs.

Each input contains:

* `name` (string)
* `type` (string, semantic type)
* `description` (string)
* `required` (boolean)

Example:

```yaml
interface:
  intent: Summarize a technical document
  inputs:
    - name: document
      type: technical_document
      description: Source document text
      required: true
```

---

### interface.outputs

Defines semantic output guarantees.

Each output contains:

* `type` (string, semantic type)
* `description` (string)
* `structure` (optional, declarative constraints)

Example:

```yaml
outputs:
  - type: structured_summary
    description: Concise technical summary
```

---

### interface.preconditions

Optional assumptions required for correctness.

Example:

```yaml
preconditions:
  - Input document is written in English
  - Input length is less than 10,000 tokens
```

---

### interface.postconditions

Optional guarantees provided by the module.

Example:

```yaml
postconditions:
  - Output contains no personally identifiable information
```

---

## dependencies

Defines dependencies on other prompt modules.

Each dependency contains:

* `name` (string)
* `version` (string, version range)

Rules:

* Cyclic dependencies are forbidden
* Resolution MUST be deterministic

Example:

```yaml
dependencies:
  - name: text-normalizer
    version: ^1.2.0
```

---

## tests

Defines unit tests for the prompt module.

Each test contains:

* `name` (string)
* `inputs` (map)
* `assertions` (list)

Assertions MAY include:

* Output contains or excludes patterns
* Output matches a structure
* Output score exceeds a threshold

Example:

```yaml
tests:
  - name: basic-summary
    inputs:
      document: example.txt
    assertions:
      - contains: "Summary"
      - max_length: 300
```

---

## Validation Rules Summary

PromptPM MUST validate that:

* All required fields are present
* Placeholders match declared inputs
* Semantic types are defined
* Versions follow semantic versioning
* Dependencies are resolvable
* Tests are well-formed

Modules failing validation MUST be rejected.

---

## Forward Compatibility

New fields may be added in future versions of this schema.

Rules:

* Existing fields MUST remain stable
* Unknown fields MUST be ignored with warnings
* Breaking schema changes require a major PromptPM version bump

---

## Compliance

A prompt module is compliant if it:

* Conforms to this schema
* Passes validation
* Passes all declared tests

This document is the authoritative reference for PromptPM prompt module definitions.
