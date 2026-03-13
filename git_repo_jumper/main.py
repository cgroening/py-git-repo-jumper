import typer
from pathlib import Path
from git_repo_jumper.cli.commands.select_command import SelectCommand
from git_repo_jumper.cli.commands.config_path_command import ConfigPathCommand
from git_repo_jumper.services.repo_service import GitRepoService
from git_repo_jumper.storage.yaml_config_storage import YamlConfigStorage
from git_repo_jumper.storage.json_git_info_storage import JsonGitInfoStorage


app = typer.Typer(help='Git Repository Jumper', invoke_without_command=True)


# Dependency composition: Wire all layers together
_config_storage = YamlConfigStorage()
_git_info_storage = JsonGitInfoStorage()
_service = GitRepoService(_config_storage, _git_info_storage)


@app.callback()
def default(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None,
        '-C', '--config',
        help='Path to the config file. If not provided, the default is used.',
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
):
    if config:
        _config_storage.set_config_path(config)

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
    ),
    use_cached_data: bool = typer.Option(
        False,
        '-c', '--cached',
        help=(
            'Reads the git status information from the cache file instead of '
            'reading git status from each repository. This is useful when '
            'you want to quickly select a repository without waiting for the '
            'git status. However, the cached data may be outdated, so use this '
            'option with caution.'
        ),
    )
):
    SelectCommand(_service).run(
        cd_only=cd_only,
        do_fetch=do_fetch,
        use_cached_data=use_cached_data
    )


# TODO: Implement this (open the recently selected repo again)
@app.command()
def recent():
    typer.echo('Command not implemented yet.')


@app.command('config-path')
def config_path():
    ConfigPathCommand(_service).run()


def main():
    app()
