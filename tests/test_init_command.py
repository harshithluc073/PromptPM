"""Unit tests for `promptpm init`."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from promptpm.cli import main


def test_init_creates_expected_files_json() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ["init", "--name", "demo-module", "--version", "1.2.3", "--json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["operation"] == "init"
        assert payload["data"]["module"] == {"name": "demo-module", "version": "1.2.3"}
        assert payload["data"]["created"] == ["promptpm.yaml", "template.prompt", "tests/"]

        assert Path("promptpm.yaml").is_file()
        assert Path("template.prompt").is_file()
        assert Path("tests").is_dir()

        config_text = Path("promptpm.yaml").read_text(encoding="utf-8")
        assert "name: demo-module" in config_text
        assert 'version: "1.2.3"' in config_text


def test_init_rejects_overwrite_existing_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("promptpm.yaml").write_text("existing", encoding="utf-8")
        result = runner.invoke(main, ["init", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert payload["operation"] == "init"
        assert payload["error"]["code"] == "VALIDATION_ERROR"
        assert "overwrite existing paths" in payload["error"]["message"]

