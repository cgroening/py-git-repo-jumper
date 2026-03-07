import typer
from git_repo_jumper.commands.list_ import ListCommand
from git_repo_jumper.services.repo_service import GitRepoService


app = typer.Typer(help='Git Repository Jumper')


# Dependency composition: Wire all layers together
_storage = None
_service = GitRepoService(_storage)


@app.command(name='list')
def list_repos():
    ListCommand(_service).run()


def main():
    app()
