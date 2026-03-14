# import pprint
import sys
from datetime import datetime
from typing import Any
from rich.console import Console
from rich.table import Table
from InquirerPy import inquirer
from InquirerPy import get_style  # type: ignore
from InquirerPy.base.control import Choice
from git_repo_jumper.cli.output import (
    print_custom_panel, print_error, print_warning, str_with_fixed_width
)
from git_repo_jumper.cli.column_widths import ColumnConfig, ColumnWidthsAdjuster
from git_repo_jumper.domain.models import Config, Repo, GitInfo
from git_repo_jumper.domain.errors import (
    ConfigNotFoundError, ConfigParseError, SelectedRepoPathSaveError,
    ConfiguredGitToolNotFoundError
)
from git_repo_jumper.services.repo_service import GitRepoService


console = Console()


class SelectCommand:
    _COLUMN_HEADERS: dict[str, str] = {
        'name': 'Repository Name',
        'current_branch_name': 'Current Branch',
        'status': 'Status',
        'github_repo_name': 'GitHub Repo Name',
    }

    _service: GitRepoService
    _cd_only: bool
    _do_fetch: bool
    _use_cached_data: bool
    _config: Config
    _visible_repos: list[Repo]


    def __init__(self, service: GitRepoService):
        self._service = service

    def run(
        self,
        cd_only: bool = False,
        do_fetch: bool = False,
        use_cached_data: bool = False
    ) -> None:
        self._cd_only = cd_only
        self._do_fetch = do_fetch
        self._use_cached_data = use_cached_data

        try:
            self._config = self._service.get_config()
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error while reading config: {str(e)}')
            return

        self._show_application_header()
        self._show_repo_selector()

    def _show_application_header(self) -> None:
        """
        Displays the application header with name and short usage instructions.
        """
        application_name = '🐙🚀 [bold cyan]Git Repository Jumper[/bold cyan]'
        instructions = 'Select a repository to [green]cd into it[/green]'
        if self._cd_only:
            instructions += '.'
        else:
            gittool = self._config.git_tool_name
            if gittool:
                instructions += f' and open it in [magenta]{gittool}[/magenta].'

        instructions += (
            '\n\n[yellow]Use arrow keys to navigate, type to filter and '
            'press Enter to select.[/yellow]'
        )

        print_custom_panel(f'{application_name}\n\n{instructions}', 'cyan')

    def _show_repo_selector(self) -> None:
        """
        Displays the repositories from the config file in a fuzzy finder and
        allows the user to select one. Repos with non-existing paths are
        excluded and shown as a warning beforehand.
        """
        if not (visible_repos := self._get_visible_repos()):
            return

        self._check_for_available_cache_data()
        self._warn_about_cache_usage()
        self._assort_invalid_repos(visible_repos)

        # Format the repositories into choices for the fuzzy finder
        self._adjust_column_widths()
        choices: list[Choice] = [
            Choice(value=i, name=self._format_fuzzy_finder_choice(repo))
            for i, repo in enumerate(self._visible_repos)
        ]

        # Show the fuzzy finder and get the selected repository index
        selected = self._create_fuzzy_finder(choices)
        self._handle_selected_repo(selected)

    def _check_for_available_cache_data(self) -> None:
        """
        Checks if cached data are available when the self._use_cached_data flag
        is set and prints a warning if not.
        """
        if self._service.cached_git_infos_available():
            return

        print_warning(
            'No cached git status data available. Run without -d/--cached flag '
            'to fetch new data.'
        )


    def _get_visible_repos(self) -> list[Repo] | None:
        """
        Returns all repositories that are not configured to be hidden;
        including git infos.
        """
        visible_repos = self._service.get_visible_repos_with_git_status(
            do_fetch=self._do_fetch,
            use_cached_data=self._use_cached_data
        )
        if not visible_repos:
            print_error('No repositories found in config.')
            return None
        return visible_repos

    def _warn_about_cache_usage(self) -> None:
        """
        Prints a warning if cached data is being used, including the age of the
        cached data.
        """
        if not self._service.cached_git_infos_available():
            return

        date_of_cached_data = self._get_date_of_cached_data()

        if self._use_cached_data:
            print_warning(
                 'Using cached git status data from '
                f'[magenta]{date_of_cached_data}[/magenta].\n'
                 'These may be outdated, so the displayed status and branch '
                 'information may not be accurate.'
            )

    def _assort_invalid_repos(self, visible_repos: list[Repo]) -> None:
        """
        Only saves repositories with valid paths to self._visible_repos and
        prints a warning listing the repositories with invalid paths.
        """
        repos_with_invalid_path: list[Repo] = []
        self._visible_repos = []
        for repo in visible_repos:
            if repo.git_info and repo.git_info.error == 'Path does not exist':
                repos_with_invalid_path.append(repo)
            else:
                self._visible_repos.append(repo)

        if repos_with_invalid_path:
            self._print_missing_paths_warning(repos_with_invalid_path)

        if not self._visible_repos:
            print_error('No repositories with valid paths found.')
            return

    def _get_date_of_cached_data(self) -> str:
        """
        Returns a human-readable string representing the date and age of the
        cached git info data, or '[unknown]' if the date is not available.
        """
        if (date_iso := self._service.date_cached_git_infos):
            try:
                dt = datetime.fromisoformat(date_iso)
                now = datetime.now().astimezone()
                minutes_ago = int((now - dt).total_seconds() / 60)

                if minutes_ago < 60:
                    ago = f'{minutes_ago} min ago'
                elif minutes_ago < 1440:
                    ago = f'{minutes_ago // 60} h ago'
                else:
                    ago = f'{minutes_ago // 1440} d ago'

                formatted = dt.strftime('%Y-%m-%d - %H:%M h')
                return f"{formatted} ({ago})"
            except ValueError:
                return '[invalid date]'
        else:
            return '[unknown]'

    @staticmethod
    def _print_missing_paths_warning(repos: list[Repo]) -> None:
        """Prints a warning panel listing all repos with non-existing paths."""
        lines = [
            '[yellow bold]⚠ Path not found for the following ' \
                +'repositories:[/yellow bold]'
        ]
        for repo in repos:
            lines.append(f'  • {repo.name}  [dim]{repo.path}[/dim]')
        print_custom_panel('\n'.join(lines), 'yellow')

    def _format_fuzzy_finder_choice(self, repo: Repo) -> str:
        """
        Formats a repository into a string for display in the fuzzy finder,
        using fixed-width columns for name, branch, status and GitHub repo name.
        Favorites are prefixed with a star.
        """
        col_widths = self._config.repo_selector_column_widths
        git_info = repo.git_info or GitInfo()
        str_fix = str_with_fixed_width

        star = '★ ' if repo.fav else '  '
        name = str_fix(repo.name, col_widths.name)
        branch = str_fix(git_info.current_branch_name or '-', col_widths.current_branch_name)
        status = str_fix(git_info.status or '-', col_widths.status)
        github_repo_name = str_fix(
            git_info.github_repo_name or '-', col_widths.github_repo_name
        )

        return f'{star}{name} │ {branch} │ {status} │ {github_repo_name}'

    def _adjust_column_widths(self) -> None:
        """
        Adjusts the column widths for the fuzzy finder based on the available
        console width and the actual content lengths of the repositories.

        Each column's max_width is derived from the longest value in the repo
        data or the column header label, whichever is greater. The
        ColumnWidthsAdjuster then distributes the available space starting from
        each column's configured min_width, respecting stretch and shrink
        priorities.

        If the console is wider than needed, extra space is allocated to
        higher-priority columns first. If the console is too narrow, higher-
        priority columns are shrunk first. The priorities for shrinking differ
        from those for stretching.
        """
        max_widths = self._calculate_max_column_widths()

        # Fixed-width overhead: star prefix (2) + 3 separators ' │ ' (3 each)
        # + fuzzy finder left padding (~5)
        overhead = 2 + 3 * 3 + 5
        col_widths = self._config.repo_selector_column_widths
        available = console.width - overhead

        column_headers = self._COLUMN_HEADERS
        column_config = {
            'name': ColumnConfig(
                min_width=col_widths.name,
                max_width=max(max_widths['name'], len(column_headers['name'])),
                stretch_priority=1, shrink_priority=4,
            ),
            'current_branch_name': ColumnConfig(
                min_width=col_widths.current_branch_name,
                max_width=max(
                    max_widths['current_branch_name'],
                    len(column_headers['current_branch_name'])
                ),
                stretch_priority=2, shrink_priority=2,
            ),
            'status': ColumnConfig(
                min_width=col_widths.status,
                max_width=max(
                    max_widths['status'], len(column_headers['status'])
                ),
                stretch_priority=3, shrink_priority=3,
            ),
            'github_repo_name': ColumnConfig(
                min_width=col_widths.github_repo_name,
                max_width=max(
                    max_widths['github_repo_name'],
                    len(column_headers['github_repo_name'])
                ),
                stretch_priority=1, shrink_priority=1,
            ),
        }

        adjuster = ColumnWidthsAdjuster(column_config, available)
        calculated = adjuster.get_calculated_widths()

        # Update the column widths in the config with the calculated widths
        for col_name, width in calculated.items():
            setattr(col_widths, col_name, width)

    def _calculate_max_column_widths(self) -> dict[str, int]:
        """
        Calculates the max width needed for each column based on the row data.
        """
        max_widths: dict[str, int] = {
            'name': 0, 'github_repo_name': 0, 'current_branch_name': 0,
            'status': 0
        }

        for repo in self._visible_repos:
            max_widths['name'] = max(max_widths['name'], len(repo.name))
            git = repo.git_info
            if not git:
                continue
            if git.github_repo_name:
                max_widths['github_repo_name'] = max(
                    max_widths['github_repo_name'], len(git.github_repo_name)
                )
            if git.current_branch_name:
                max_widths['current_branch_name'] = max(
                    max_widths['current_branch_name'], len(git.current_branch_name)
                )
            if git.status:
                max_widths['status'] = max(
                    max_widths['status'], len(git.status)
                )

        return max_widths

    def _create_fuzzy_finder(self, choices: list[Choice]) -> Any:
        """
        Creates and returns an InquirerPy fuzzy finder prompt with the given
        choices.
        """
        col_widths = self._config.repo_selector_column_widths

        fix_str = str_with_fixed_width

        headers = self._COLUMN_HEADERS
        name = fix_str(headers['name'], col_widths.name)
        branch = fix_str(
            headers['current_branch_name'], col_widths.current_branch_name
        )
        status = fix_str(headers['status'], col_widths.status)
        github_repo_name = headers['github_repo_name']

        header_line = f'     {name} │ {branch} │ {status} │ {github_repo_name}'

        print()  # Empty line for better spacing before the prompt
        return inquirer.fuzzy(  # type: ignore
            message=header_line,
            choices=choices,
            qmark='',
            default='',
            max_height='90%',
            border=True,
            info=True,
            match_exact=False,
            marker='❯',
            marker_pl=' ',
            style=get_style({
                'question': 'bold', 'pointer': 'fg:#f4f4f4 bg:#522a37'
            }, style_override=False)
        ).execute()

    def _handle_selected_repo(self, selected_id: int | None) -> None:
        """
        Handles the selected repository by storing its path, printing its
        details and optionally opening the git tool.
        """
        repos = self._visible_repos

        if not repos or selected_id is None or \
            selected_id < 0 or selected_id >= len(repos):
            print_warning('Selection cancelled.')
            return

        selected_path = repos[selected_id].path

        # Store the selected repository path for use in the 'cd' command
        self._store_selected_repo_path(selected_path)

        # Get the name of the git tool to open, if not in cd-only mode
        git_tool_name = None
        if not self._cd_only:
            if not self._config.git_tool_name:
                print_warning('No git tool configured.')
            else:
                git_tool_name = self._config.git_tool_name

        # Print the selected repo details and the git tool that will be opened
        self._print_selected_repo(repos[selected_id], git_tool_name)

        # Open the git tool if not in cd-only mode and a tool is configured
        if not self._cd_only and git_tool_name:
            try:
                self._service.open_git_tool(selected_path, git_tool_name)
            except ConfiguredGitToolNotFoundError as e:
                print_error(str(e))
                sys.exit(1)
            except Exception as e:
                print_error(f'Unexpected error while opening git tool: {str(e)}')
                sys.exit(1)

    def _store_selected_repo_path(self, path: str) -> None:
        """Stores the selected repository path in a temporary file."""
        try:
            self._service.store_selected_repo_path(path)
        except SelectedRepoPathSaveError as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(
                f'Unexpected error while storing selected path: {str(e)}'
            )
            return

    @staticmethod
    def _print_selected_repo(
        repo: Repo, git_program_name: str | None = None
    ) -> None:
        """Prints details of the selected repository in a Rich table."""
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
