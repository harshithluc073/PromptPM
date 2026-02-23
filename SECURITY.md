# Security

## 1. Security model overview
PromptPM manages prompt module definitions and metadata. It is designed for deterministic, local-first package management, not runtime prompt execution.

Current security priorities are:

- **Supply chain safety**: modules are validated before install/publish, and published versions are immutable.
- **Deterministic behavior**: CLI output, dependency resolution, and test execution are deterministic to reduce ambiguous states in automation.
- **Local registry integrity**: installed modules are stored in a deterministic directory layout and checked against immutability manifests.
- **Untrusted content handling**: prompt/module content is treated as data and should not be executed by PromptPM.

## 2. What PromptPM does not do
PromptPM does not currently provide:

- Prompt execution, model invocation, or agent runtime isolation.
- Remote registry trust management, signing, or key infrastructure.
- Secret management, access control, or authorization systems.
- Malware scanning of arbitrary files outside defined validation checks.
- Network-based security controls.

If you need those controls, enforce them in surrounding infrastructure.

## 3. Supported threat model
PromptPM is intended to reduce risk in these areas:

- **Module tampering after publish**: immutable versions and manifest verification detect post-publish changes.
- **Non-deterministic dependency outcomes**: deterministic semver resolution and ordering reduce inconsistent installs.
- **Unsafe registry path inputs**: registry operations are constrained to local filesystem paths in current command behavior.
- **Schema/contract drift**: validation and tests provide early failure before publish and install workflows.

Out of scope for PromptPM itself:

- Compromise of the host machine or filesystem.
- Malicious execution performed by external tooling that consumes prompt files.
- Organization-level identity, permissions, and CI secret exposure.

## 4. How to report vulnerabilities
Please report suspected vulnerabilities with enough detail to reproduce:

1. Affected PromptPM version and environment (OS, Python version).
2. Exact command(s) and input module files used.
3. Expected behavior vs. actual behavior.
4. Impact assessment (what an attacker can do).
5. Minimal reproduction steps or proof of concept.

Use the project issue tracker for reports. If public disclosure would create immediate risk, share minimal details first and request a private follow-up path from maintainers.

## 5. Disclosure policy
PromptPM follows a practical coordinated disclosure process:

1. Confirm and triage the report.
2. Reproduce and scope affected behavior.
3. Prepare and review a fix with tests.
4. Release the fix and document the change.
5. Publish issue details after a fix is available.

There is no fixed response SLA. Reports that include clear reproduction steps are handled more quickly.
