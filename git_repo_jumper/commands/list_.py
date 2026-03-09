# import pprint
import math
from typing import Any
from rich.console import Console
from rich.table import Table
from InquirerPy import inquirer
from InquirerPy import get_style  # type: ignore
from InquirerPy.base.control import Choice
from git_repo_jumper.output import print_custom_panel, print_error, print_warning
from git_repo_jumper.domain.models import Config, Repo, GitInfo
from git_repo_jumper.domain.errors import (
    ConfigNotFoundError, ConfigParseError, SelectedRepoPathSaveError
)
from git_repo_jumper.services.repo_service import GitRepoService


console = Console()


class ListCommand:
    _service: GitRepoService
    _cd_only: bool
    _do_fetch: bool
    _config: Config
    _visible_repos: list[Repo]

    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self, cd_only: bool = False, do_fetch: bool = False) -> None:
        self._cd_only = cd_only
        self._do_fetch = do_fetch

        try:
            self._config = self._service.get_config()
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error while reading config: {str(e)}')
            return

        self.show_application_header()
        self.show_repo_selector()

    def show_application_header(self) -> None:
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

    def show_repo_selector(self) -> None:
        """
        Displays the repositories from the config file in a fuzzy finder and
        allows the user to select one. Repos with non-existing paths are
        excluded and shown as a warning beforehand.
        """
        all_repos = self._service.get_visible_repos_with_git_status(
            do_fetch=self._do_fetch
        )
        if not all_repos:
            print_error('No repositories found in config.')
            return

        # Separate repos with missing paths from valid ones
        repos_with_invalid_path: list[Repo] = []
        self._visible_repos = []
        for repo in all_repos:
            if repo.git_info and repo.git_info.error == 'Path does not exist':
                repos_with_invalid_path.append(repo)
            else:
                self._visible_repos.append(repo)

        if repos_with_invalid_path:
            self._print_missing_paths_warning(repos_with_invalid_path)

        if not self._visible_repos:
            print_error('No repositories with valid paths found.')
            return

        # Format the repositories into choices for the fuzzy finder
        self._adjust_column_widths()
        choices: list[Choice] = [
            Choice(value=i, name=self.format_fuzzy_finder_choice(repo))
            for i, repo in enumerate(self._visible_repos)
        ]

        # Show the fuzzy finder and get the selected repository index
        selected = self.create_fuzzy_finder(choices)
        self.handle_selected_repo(selected)

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

    def format_fuzzy_finder_choice(self, repo: Repo) -> str:
        """
        Formats a repository into a string for display in the fuzzy finder,
        using fixed-width columns for name, branch, status and GitHub repo name.
        Favorites are prefixed with a star.
        """
        col_widths = self._config.repo_selector_column_widths
        git_info = repo.git_info or GitInfo()
        str_fix = self.str_with_fixed_width

        star = '★ ' if repo.fav else '  '
        name = str_fix(repo.name, col_widths.name)
        branch = str_fix(git_info.branch or '-', col_widths.branch)
        status = str_fix(git_info.status or '-', col_widths.status)
        github_repo_name = str_fix(
            git_info.github_repo_name or '-', col_widths.github_repo_name
        )

        return f'{star}{name} │ {branch} │ {status} │ {github_repo_name}'

    def _adjust_column_widths(self) -> None:
        """
        Calculates the necessary column widths for the fuzzy finder based on
        the longest values among the repositories. If the column widths in the
        config are too small to fit the longest values, they are increased
        based on the available console width and the priority of the columns.

        The "Repository Name" and "GitHub Repo Name" columns have the highest
        priority: Extra space is first allocated to them equally until they can
        fit their longest values or the console width is reached.
        Then the "Current Branch" column gets extra space and finally the
        "Status" column.

        If the console width is too small to maintain the column width in the
        config, the columns "Reository Name" and "GitHub Repo Name" are shrunk
        equally until they fit.
        """
        # Calculate the max width needed for each column based on the repo data
        max_widths: dict[str, int] = {
            'name': 0, 'github_repo_name': 0, 'branch': 0, 'status': 0
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
            if git.branch:
                max_widths['branch'] = max(max_widths['branch'], len(git.branch))
            if git.status:
                max_widths['status'] = max(max_widths['status'], len(git.status))

        # Calculate available space
        col_widths = self._config.repo_selector_column_widths

        # Fixed-width overhead: star prefix (2) + 3 separators ' │ ' (3 each)
        # + fuzzy finder left padding (~5)
        overhead = 2 + 3 * 3 + 5
        available = console.width - col_widths.total() - overhead

        # Not enough space: shrink name and github_repo_name equally
        if available < 0:
            deficit = -available
            shrink_each = math.ceil(deficit / 2)
            col_widths.name = max(1, col_widths.name - shrink_each)
            col_widths.github_repo_name = max(
                1, col_widths.github_repo_name - (deficit - shrink_each)
            )
            return

        if available == 0:
            return

        # Priority groups: equal-priority columns are grouped together
        priority_groups: list[list[str]] = [
            ['name', 'github_repo_name'],
            ['branch'],
            ['status'],
        ]

        # Allocate extra space to columns based on priority until available
        # space is used up
        for group in priority_groups:
            if available <= 0:
                break

            # Calculate how much extra width each column in the group needs
            needs = {
                col: max(0, max_widths[col] - getattr(col_widths, col))
                for col in group
            }
            total_need = sum(needs.values())
            if total_need == 0:
                continue

            # Don't allocate more than what's available or needed
            budget = min(available, total_need)
            gives: dict[str, int] = {col: 0 for col in group}
            remaining = budget

            # First pass: give each column an equal share, capped at its need
            share = remaining / len(group)
            for col in group:
                gives[col] = min(needs[col], math.floor(share))
                remaining -= gives[col]

            # Second pass: distribute leftover to columns that still need more
            # (e.g. when one column needed less than its share)
            for col in group:
                if remaining <= 0:
                    break
                extra = min(needs[col] - gives[col], remaining)
                gives[col] += extra
                remaining -= extra

            # Apply the calculated increases
            for col in group:
                setattr(col_widths, col, getattr(col_widths, col) + gives[col])

            available -= (budget - remaining)

    # TODO: Put this method in a separate utility module and add unit tests for it
    @staticmethod
    def str_with_fixed_width(text: str, width: int, align: str = 'left') -> str:
        """
        Returns a string truncated or padded to fit the specified width.
        Alignment can be 'start', 'end', or 'center'.
        """
        if len(text) > width:
            if align == 'right':
                return '…' + text[-(width - 1):]  # Truncate from left
            return text[:width - 1] + '…'         # Truncate from right

        if align == 'left':
            return text.ljust(width)
        elif align == 'right':
            return text.rjust(width)
        elif align == 'center':
            return text.center(width)
        else:
            raise ValueError(f'Invalid alignment: {align}')

    def create_fuzzy_finder(self, choices: list[Choice]) -> Any:
        """
        Creates and returns an InquirerPy fuzzy finder prompt with the given
        choices.
        """
        col_widths = self._config.repo_selector_column_widths

        fix_str = self.str_with_fixed_width

        name = fix_str('Repository Name', col_widths.name)
        branch = fix_str('Current Branch', col_widths.branch)
        status = fix_str('Status', col_widths.status)
        github_repo_name = 'GitHub Repo Name'

        header_line = f'     {name} │ {branch} │ {status} │ {github_repo_name}'

        print()  # Empty line for better spacing before the prompt
        return inquirer.fuzzy(  # type: ignore
            message=header_line,
            choices=choices,
            default='',
            max_height='90%',
            border=True,
            info=True,
            match_exact=False,
            marker='❯',
            marker_pl=' ',
            qmark='',
            style=get_style({
                'question': 'bold', 'pointer': 'fg:#f4f4f4 bg:#522a37'
            }, style_override=False)
        ).execute()

    # TODO: Refactor this method to separate concerns (e.g. storing path, printing details, opening tool)
    def handle_selected_repo(self, selected_id: int) -> None:
        """
        Handles the selected repository by storing its path, printing its
        details and optionally opening the git tool.
        """
        repos = self._visible_repos

        if not repos:
            return

        if selected_id < 0 or selected_id >= len(repos):
            print_warning('Selection cancelled.')
            return

        # Store the selected repository path for use in the 'cd' command
        try:
            self._service.store_selected_repo_path(repos[selected_id].path)
        except SelectedRepoPathSaveError as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(
                f'Unexpected error while storing selected path: {str(e)}'
            )
            return

        # Get the name of the git tool to open, if not in cd-only mode
        git_tool_name = None
        if not self._cd_only:
            if not self._config.git_tool_name:
                print_warning('No git tool configured.')
            else:
                git_tool_name = self._config.git_tool_name

        # Print the selected repo details and the git tool that will be opened
        self.print_selected_repo(repos[selected_id], git_tool_name)

        # Open the git tool if not in cd-only mode and a tool is configured
        if not self._cd_only and git_tool_name:
            try:
                self._service.open_git_tool(repos[selected_id].path, git_tool_name)
            except Exception as e:
                print_error(f'Error opening git tool: {str(e)}')

    @staticmethod
    def print_selected_repo(
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
