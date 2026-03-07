import pprint
from rich.console import Console
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from git_repo_jumper.output import print_error
from git_repo_jumper.domain.models import Repo
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.services.repo_service import GitRepoService


console = Console()
print = console.print


class ListCommand:
    _service: GitRepoService
    _cd_only: bool

    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self, cd_only: bool) -> None:
        self._cd_only = cd_only

        try:
            repos: list[Repo] | None = self._service.fetch_repos()
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error: {str(e)}')
            return

        self.print_repos(repos)

    @staticmethod
    def print_repos(repos: list[Repo] | None) -> None:
        if not repos:
            print_error('No repositories found in config.')
            return

        # Select repository with fuzzy finder (table-like format)
        choices: list[Choice] = []
        repo_map: dict[str, str] = {}

        for r in repos:
            choice_text = r.name
            choices.append(
                Choice(value={'name': r.name, 'path': r.path}, name=choice_text)
            )
            repo_map[choice_text] = r.name

        selected = inquirer.fuzzy(  # type: ignore
            message='Select repository (type to filter):',
            choices=choices,
            default='',
            max_height='90%',
            border=True,
            info=True,
            match_exact=False,
            marker='❯',
            marker_pl=' ',
        ).execute()

        if not selected:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return

        print(selected)


