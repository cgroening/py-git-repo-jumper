import typer
from pathlib import Path
from git_repo_jumper.cli.commands.select_command import SelectCommand
from git_repo_jumper.services.repo_service import GitRepoService
from git_repo_jumper.storage.yaml_config_storage import YamlConfigStorage


app = typer.Typer(help='Git Repository Jumper', invoke_without_command=True)


# Dependency composition: Wire all layers together
_storage = YamlConfigStorage()
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
        SelectCommand(_service).run()


@app.command()
def select(
    cd_only: bool = typer.Option(
        False,
        '-s', '--save-only',
        help=(
            'Save path of selected repo to selected-repo.txt (in parent folder '
            'of config file) without opening the configured git tool.'
        ),
    ),
    do_fetch: bool = typer.Option(
        False,
        '-f', '--fetch',
        help=(
            'Fetch the latest git status for each remote repository before '
            'showing the selector. Use this only when necessary, because this '
            'may take some time; especially if you have many repositories or a '
            'slow network connection.'
        ),
    )
):
    SelectCommand(_service).run(cd_only=cd_only, do_fetch=do_fetch)


# TODO: Implement this (open the recentl selected repo again)
@app.command()
def recent():
    typer.echo('Command not implemented yet.')


# TODO: Implement this (return path of the config file)
@app.command()
def config():
    typer.echo('Command not implemented yet.')


def main():
    app()
