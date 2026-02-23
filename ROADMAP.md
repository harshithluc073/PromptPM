# PromptPM Roadmap

This roadmap describes the intended evolution of PromptPM based on the current architecture and specification documents. It is intentionally conservative and focused on correctness over scope expansion.

## Current Version (v0.1.x)
- Core CLI lifecycle is implemented: `init`, `validate`, `test`, `install`, `publish`, `list`, and `info`.
  The baseline command surface is available and scriptable.
- Deterministic output modes and exit codes are in place.
  CLI behavior is suitable for automation and CI gating.
- Local filesystem registry is operational with immutable published versions.
  Registry behavior is local-first and does not require network access.
- Semantic version parsing and range resolution are implemented.
  Dependency selection is deterministic and follows semver rules.
- Dependency resolution includes transitive traversal and cycle detection.
  Invalid graphs fail fast with explicit errors.
- Prompt module unit test execution is available with structured diagnostics.
  Module quality checks can be enforced before publish.

## Near-Term Goals (v0.2.x)
- Close remaining gaps between implementation and full SPEC requirements.
  Priority is end-to-end enforcement of documented behavior, not new surface area.
- Expand semantic validation depth for module contracts.
  Validation should cover more interface-level guarantees with actionable errors.
- Strengthen CLI contract conformance testing.
  Add broader tests for output stability, error codes, and edge-case exit behavior.
- Formalize deterministic configuration loading via `--config`.
  Configuration handling should be explicit, predictable, and easy to audit.
- Improve developer documentation for module authoring and CI usage.
  Focus on practical, minimal workflows that match implemented behavior.

## Mid-Term Goals (v0.3.x)
- Introduce a pluggable registry abstraction while keeping local-first as the default.
  This enables broader deployment models without changing command semantics.
- Add deterministic dependency lock artifacts.
  Resolved dependency graphs should be reproducible across environments.
- Implement stronger compatibility analysis across module versions and dependencies.
  Compatibility decisions should be explicit and explainable.
- Extend test-runner capabilities within schema-defined boundaries.
  Additional assertions should preserve deterministic execution and clear diagnostics.
- Improve operational tooling around module integrity and auditability.
  Registry and module checks should remain transparent and machine-verifiable.

## Long-Term Goals (v1.0)
- Publish a stable, fully enforced specification baseline.
  `SPEC.md`, schema, and CLI contract should be aligned and treated as compatibility commitments.
- Provide strong backward-compatibility guarantees for stable CLI behavior.
  Breaking changes should require explicit process and versioning discipline.
- Deliver complete spec-first module lifecycle coverage.
  Authoring, validation, testing, dependency management, and publishing should be coherent and predictable.
- Establish a mature conformance and regression test suite.
  Determinism and contract adherence should be continuously verifiable.
- Reach production-grade maintainability standards.
  Documentation, contributor workflows, and release discipline should support long-term project stewardship.
