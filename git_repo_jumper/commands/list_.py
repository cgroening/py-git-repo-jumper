import pprint
from rich.console import Console
from rich.table import Table
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from git_repo_jumper.output import print_error, print_warning, print_success, print_info, print_custom_panel
from git_repo_jumper.domain.models import Config, Repo
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.services.repo_service import GitRepoService


console = Console()


class ListCommand:
    _service: GitRepoService
    _cd_only: bool
    _config: Config

    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self, cd_only: bool = False) -> None:
        self._cd_only = cd_only

        try:
            self._config = self._service.get_config()
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error: {str(e)}')
            return

        self.print_repos()

    def print_repos(self) -> None:
        repos = self._config.repos
        if not repos:
            print_error('No repositories found in config.')
            return

        # Select repository with fuzzy finder (table-like format)
        choices: list[Choice] = []

        for i, repo in enumerate(repos):
            choices.append(Choice(value=i, name=repo.name))

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

        if not isinstance(selected, int):
            print_warning('Selection cancelled.')
            return

        self._service.store_selected_repo_path(repos[selected].path)

        if self._cd_only:
            self.print_selected_repo(repos[selected])
        else:
            self.print_selected_repo(repos[selected], 'lazygit')

    @staticmethod
    def print_selected_repo(
        repo: Repo, git_program_name: str | None = None
    ) -> None:
        table = Table(title='[cyan]ℹ Selected Repository[/cyan]',
                      show_header=False, show_lines=True)
        table.add_column(style='bold', overflow='fold')
        table.add_column(overflow='fold')
        table.add_row('Name:', f'[yellow]{repo.name}[/yellow]')
        table.add_row('Path:', f'[magenta]{repo.path}[/magenta]')

        if git_program_name:
            table.add_row(
                'Opening in:', f'[green]{git_program_name}[/green]'
            )

        console.print(table)


