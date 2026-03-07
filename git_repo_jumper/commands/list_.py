import typer
import pprint
from pathlib import Path
from rich.console import Console
from git_repo_jumper.output import print_error
from git_repo_jumper.services.repo_service import GitRepoService
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError


console = Console()
print = console.print


class ListCommand:
    _service: GitRepoService


    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self, config_path: Path | None = None) -> None:
        try:
            config = self._service.list_repos(config_path)
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error: {str(e)}')
            return

        console.print(pprint.pformat(config))
