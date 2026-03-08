import sys
import typer
from pathlib import Path
from git_repo_jumper.output import print_error
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.commands.list_ import ListCommand
from git_repo_jumper.services.repo_service import GitRepoService
from git_repo_jumper.storage.yaml_config_storage import YamlConfigStorage


app = typer.Typer(help='Git Repository Jumper', invoke_without_command=True)


# Dependency composition: Wire all layers together
_storage = YamlConfigStorage()


# try:
#     _storage = YamlConfigStorage()
# except (ConfigNotFoundError, ConfigParseError) as e:
#     print_error(str(e))
#     sys.exit(1)
# except Exception as e:
#     print_error(f'Unexpected error: {str(e)}')
#     sys.exit(1)

_service = GitRepoService(_storage)


@app.callback()
def default(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None,
        '-c', '--config',
        help='Path to the config file. If not provided, the default is used.',
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
):
    if config:
        _storage.set_config_path(config)

    if ctx.invoked_subcommand is None:
        ListCommand(_service).run()


# TODO: Remove this:
@app.command()
def test():
    typer.echo('Test command called')


@app.command(name='list')
def list_repos(
    cd_only: bool = typer.Option(
        False,
        '-s', '--save-only',
        help=(
            'Save path of selected repo to last-repo.txt without opening '
            'the configured git tool.'),
    )
):
    ListCommand(_service).run(cd_only=cd_only)


def main():
    app()
