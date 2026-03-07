import pprint
from rich.console import Console
from git_repo_jumper.output import print_error
from git_repo_jumper.domain.models import Repo
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.services.repo_service import GitRepoService


console = Console()
print = console.print


class ListCommand:
    _service: GitRepoService


    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self) -> None:
        try:
            repos: list[Repo] | None = self._service.fetch_repos()
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error: {str(e)}')
            return

        console.print(pprint.pformat(repos))
