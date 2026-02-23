"""Deterministic prompt module test runner."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from promptpm.core.errors import ValidationError
from promptpm.core.schema import load_prompt_module, validate_prompt_module

__test__ = False


@dataclass(frozen=True)
class AssertionFailure:
    """Single assertion failure record."""

    test_name: str
    assertion_index: int
    assertion_type: str
    message: str
    expected: str
    actual: str


@dataclass(frozen=True)
class TestCaseResult:
    """Result for one test case."""

    name: str
    passed: bool
    failures: tuple[AssertionFailure, ...]


@dataclass(frozen=True)
class TestRunResult:
    """Aggregate run summary for module tests."""

    total: int
    passed: int
    failed: int
    results: tuple[TestCaseResult, ...]


@dataclass(frozen=True)
class _ParsedTestCase:
    name: str
    inputs: dict[str, Any]
    assertions: tuple[dict[str, Any], ...]
    original_index: int


def run_prompt_module_tests(module_path: str) -> TestRunResult:
    """Run module tests deterministically."""
    module = load_prompt_module(module_path)
    validate_prompt_module(module)

    parsed_tests = _parse_tests(module.tests)
    template = _load_template(module.source_path, module.prompt)
    module_root = os.path.dirname(os.path.abspath(module.source_path))

    case_results: list[TestCaseResult] = []
    for test_case in parsed_tests:
        rendered_output = _render_template(template, test_case.inputs, module_root)
        failures = _evaluate_assertions(
            test_name=test_case.name,
            output_text=rendered_output,
            assertions=test_case.assertions,
        )
        case_results.append(
            TestCaseResult(
                name=test_case.name,
                passed=len(failures) == 0,
                failures=tuple(failures),
            )
        )

    total = len(case_results)
    passed = sum(1 for result in case_results if result.passed)
    failed = total - passed

    return TestRunResult(
        total=total,
        passed=passed,
        failed=failed,
        results=tuple(case_results),
    )


def _load_template(source_path: str, prompt_block: dict[str, Any]) -> str:
    template_rel = prompt_block.get("template")
    if not isinstance(template_rel, str) or not template_rel:
        raise ValidationError("prompt.template must be a non-empty string")

    module_root = os.path.dirname(os.path.abspath(source_path))
    template_path = os.path.abspath(os.path.join(module_root, template_rel))
    if not os.path.isfile(template_path):
        raise ValidationError(f"Template file not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as handle:
        return handle.read()


def _parse_tests(raw_tests: Any) -> tuple[_ParsedTestCase, ...]:
    if raw_tests in (None, []):
        return tuple()

    if not isinstance(raw_tests, list):
        raise ValidationError("tests must be a list")

    parsed: list[_ParsedTestCase] = []
    for index, test_case in enumerate(raw_tests):
        if not isinstance(test_case, dict):
            raise ValidationError(f"tests[{index}] must be a mapping")

        name = test_case.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError(f"tests[{index}].name must be a non-empty string")

        inputs = test_case.get("inputs", {})
        if not isinstance(inputs, dict):
            raise ValidationError(f"tests[{index}].inputs must be a mapping")

        assertions = test_case.get("assertions")
        if not isinstance(assertions, list):
            raise ValidationError(f"tests[{index}].assertions must be a list")

        normalized_assertions: list[dict[str, Any]] = []
        for assertion_index, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                raise ValidationError(
                    f"tests[{index}].assertions[{assertion_index}] must be a mapping"
                )
            if len(assertion) != 1:
                raise ValidationError(
                    f"tests[{index}].assertions[{assertion_index}] must define exactly one assertion"
                )
            normalized_assertions.append(assertion)

        parsed.append(
            _ParsedTestCase(
                name=name.strip(),
                inputs=dict(inputs),
                assertions=tuple(normalized_assertions),
                original_index=index,
            )
        )

    parsed.sort(key=lambda entry: (entry.name, entry.original_index))
    return tuple(parsed)


def _render_template(template: str, inputs: dict[str, Any], module_root: str) -> str:
    rendered = template
    for key in sorted(inputs):
        value = _resolve_input_value(inputs[key], module_root)
        value_text = _stringify_value(value)
        rendered = rendered.replace(f"{{{{{key}}}}}", value_text)
        rendered = rendered.replace(f"{{{key}}}", value_text)
    return rendered


def _resolve_input_value(value: Any, module_root: str) -> Any:
    if isinstance(value, str):
        candidate_path = os.path.abspath(os.path.join(module_root, value))
        if os.path.isfile(candidate_path):
            with open(candidate_path, "r", encoding="utf-8") as handle:
                return handle.read()
        return value
    return value


def _stringify_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _evaluate_assertions(
    *,
    test_name: str,
    output_text: str,
    assertions: tuple[dict[str, Any], ...],
) -> list[AssertionFailure]:
    failures: list[AssertionFailure] = []

    for index, assertion in enumerate(assertions):
        assertion_type = next(iter(assertion.keys()))
        assertion_value = assertion[assertion_type]

        if assertion_type == "contains":
            _ensure_string_assertion(assertion_type, assertion_value, test_name, index)
            if assertion_value not in output_text:
                failures.append(
                    _failure(
                        test_name=test_name,
                        assertion_index=index,
                        assertion_type=assertion_type,
                        message=f"Expected output to contain {assertion_value!r}",
                        expected=assertion_value,
                        actual=_preview(output_text),
                    )
                )
            continue

        if assertion_type == "excludes":
            _ensure_string_assertion(assertion_type, assertion_value, test_name, index)
            if assertion_value in output_text:
                failures.append(
                    _failure(
                        test_name=test_name,
                        assertion_index=index,
                        assertion_type=assertion_type,
                        message=f"Expected output to exclude {assertion_value!r}",
                        expected=assertion_value,
                        actual=_preview(output_text),
                    )
                )
            continue

        if assertion_type == "max_length":
            _ensure_int_assertion(assertion_type, assertion_value, test_name, index)
            actual_length = len(output_text)
            if actual_length > assertion_value:
                failures.append(
                    _failure(
                        test_name=test_name,
                        assertion_index=index,
                        assertion_type=assertion_type,
                        message=(
                            f"Expected output length <= {assertion_value}, "
                            f"got {actual_length}"
                        ),
                        expected=str(assertion_value),
                        actual=str(actual_length),
                    )
                )
            continue

        if assertion_type == "structure":
            structure_failure = _evaluate_structure_assertion(
                test_name=test_name,
                assertion_index=index,
                output_text=output_text,
                assertion_value=assertion_value,
            )
            if structure_failure is not None:
                failures.append(structure_failure)
            continue

        raise ValidationError(
            f"Unsupported assertion type in test {test_name!r} at index {index}: "
            f"{assertion_type!r}"
        )

    return failures


def _evaluate_structure_assertion(
    *,
    test_name: str,
    assertion_index: int,
    output_text: str,
    assertion_value: Any,
) -> AssertionFailure | None:
    expected_type = "json_object"
    required_keys: list[str] = []

    if isinstance(assertion_value, str):
        expected_type = assertion_value
    elif isinstance(assertion_value, dict):
        raw_type = assertion_value.get("type", "json_object")
        if not isinstance(raw_type, str):
            raise ValidationError(
                f"structure assertion type must be a string in test {test_name!r} "
                f"at index {assertion_index}"
            )
        expected_type = raw_type

        raw_keys = assertion_value.get("required_keys", [])
        if raw_keys not in (None, []) and not isinstance(raw_keys, list):
            raise ValidationError(
                f"structure.required_keys must be a list in test {test_name!r} "
                f"at index {assertion_index}"
            )
        for key in raw_keys or []:
            if not isinstance(key, str) or not key:
                raise ValidationError(
                    f"structure.required_keys entries must be non-empty strings in "
                    f"test {test_name!r} at index {assertion_index}"
                )
            required_keys.append(key)
    else:
        raise ValidationError(
            f"structure assertion must be a string or mapping in test {test_name!r} "
            f"at index {assertion_index}"
        )

    if expected_type not in {"json_object", "json_array"}:
        raise ValidationError(
            f"Unsupported structure type in test {test_name!r} at index {assertion_index}: "
            f"{expected_type!r}"
        )

    try:
        parsed_output = json.loads(output_text)
    except json.JSONDecodeError:
        return _failure(
            test_name=test_name,
            assertion_index=assertion_index,
            assertion_type="structure",
            message="Expected valid JSON output",
            expected=expected_type,
            actual=_preview(output_text),
        )

    if expected_type == "json_object":
        if not isinstance(parsed_output, dict):
            return _failure(
                test_name=test_name,
                assertion_index=assertion_index,
                assertion_type="structure",
                message="Expected JSON object output",
                expected="object",
                actual=type(parsed_output).__name__,
            )
        if required_keys:
            missing = [key for key in required_keys if key not in parsed_output]
            if missing:
                return _failure(
                    test_name=test_name,
                    assertion_index=assertion_index,
                    assertion_type="structure",
                    message=f"Missing required JSON keys: {', '.join(missing)}",
                    expected=json.dumps(required_keys),
                    actual=json.dumps(sorted(parsed_output.keys())),
                )

    if expected_type == "json_array" and not isinstance(parsed_output, list):
        return _failure(
            test_name=test_name,
            assertion_index=assertion_index,
            assertion_type="structure",
            message="Expected JSON array output",
            expected="array",
            actual=type(parsed_output).__name__,
        )

    return None


def _ensure_string_assertion(
    assertion_type: str,
    assertion_value: Any,
    test_name: str,
    assertion_index: int,
) -> None:
    if not isinstance(assertion_value, str):
        raise ValidationError(
            f"{assertion_type} assertion must be a string in test {test_name!r} "
            f"at index {assertion_index}"
        )


def _ensure_int_assertion(
    assertion_type: str,
    assertion_value: Any,
    test_name: str,
    assertion_index: int,
) -> None:
    if not isinstance(assertion_value, int) or assertion_value < 0:
        raise ValidationError(
            f"{assertion_type} assertion must be a non-negative integer in "
            f"test {test_name!r} at index {assertion_index}"
        )


def _failure(
    *,
    test_name: str,
    assertion_index: int,
    assertion_type: str,
    message: str,
    expected: str,
    actual: str,
) -> AssertionFailure:
    return AssertionFailure(
        test_name=test_name,
        assertion_index=assertion_index,
        assertion_type=assertion_type,
        message=message,
        expected=expected,
        actual=actual,
    )


def _preview(value: str, *, limit: int = 120) -> str:
    normalized = value.replace("\n", "\\n")
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
