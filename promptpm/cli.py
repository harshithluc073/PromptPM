"""PromptPM CLI entrypoint."""

from __future__ import annotations

import click

from promptpm.commands import info, init, install, list as list_command, publish, test, validate
from promptpm.version import __version__


@click.group()
@click.version_option(version=__version__, prog_name="promptpm")
@click.option("--json", "json_output", is_flag=True, help="Force JSON output.")
@click.option("--pretty", "pretty_output", is_flag=True, help="Pretty human-readable output.")
@click.option("--quiet", is_flag=True, help="Suppress non-error output.")
@click.option("--config", "config_path", default=None, help="Path to PromptPM config file.")
@click.option(
    "--registry",
    "registry_path",
    default=".promptpm_registry",
    show_default=True,
    help="Local registry path.",
)
@click.pass_context
def main(
    ctx: click.Context,
    json_output: bool,
    pretty_output: bool,
    quiet: bool,
    config_path: str | None,
    registry_path: str,
) -> None:
    """PromptPM CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json_output"] = json_output
    ctx.obj["pretty_output"] = pretty_output
    ctx.obj["quiet"] = quiet
    ctx.obj["config_path"] = config_path
    ctx.obj["registry_path"] = registry_path


main.add_command(init.command)
main.add_command(info.command)
main.add_command(list_command.command)
main.add_command(publish.command)
main.add_command(test.command)
main.add_command(install.command)
main.add_command(validate.command)


if __name__ == "__main__":
    main()
