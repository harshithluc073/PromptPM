"""Contract-level CLI compliance checks."""

from __future__ import annotations

import json

from click.testing import CliRunner

from promptpm.cli import main


def test_cli_help_has_required_contract_flags_and_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    output = result.output

    for flag in ("--config", "--registry", "--quiet", "--json", "--version"):
        assert flag in output

    for command in ("init", "validate", "test", "install", "publish", "list", "info"):
        assert command in output


def test_cli_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_quiet_suppresses_success_output(tmp_path) -> None:
    registry_root = tmp_path / "registry"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--quiet", "--registry", str(registry_root), "list", "--json"],
    )

    assert result.exit_code == 0
    assert result.output == ""


def test_quiet_does_not_suppress_error_output() -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--quiet",
            "--registry",
            "https://registry.example.com/promptpm",
            "list",
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "DEPENDENCY_ERROR"

