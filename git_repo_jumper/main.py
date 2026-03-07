import typer
from pathlib import Path
from git_repo_jumper.commands.list_ import ListCommand
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
        help='Path to the config file. If not provied, the default is used.',
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
):
    if config:
        _storage.set_config_path(config)

    if ctx.invoked_subcommand is None:
        typer.echo('No command provided. Runnig command "list" by default.')
        ListCommand(_service).run()


@app.command()
def test():
    typer.echo('Test command called')


@app.command(name='list')
def list_repos():
    ListCommand(_service).run()


def main():
    app()
