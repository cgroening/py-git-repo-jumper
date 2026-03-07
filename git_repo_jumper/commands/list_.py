import typer
from git_repo_jumper.services.repo_service import GitRepoService


class ListCommand:
    _service: GitRepoService


    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self) -> None:
        typer.echo('List command called')
