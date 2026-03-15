from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from git_repo_jumper.cli.commands.select import SelectCommand
from git_repo_jumper.domain.models import (
    Config, Repo, GitInfo, RepoSelectorColumnWidths
)
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError


def make_config(**kwargs):
    defaults = dict(
        config_path=Path('/fake/config.yaml'),
        repo_selector_column_widths=RepoSelectorColumnWidths(
            name=20, current_branch_name=15, status=10, github_repo_name=20
        ),
        git_tool_name='lazygit',
        github_username='testuser',
        repos=[],
    )
    defaults.update(kwargs)
    return Config(**defaults)  # type: ignore


def make_command(config=None):
    service = MagicMock()
    service.get_config.return_value = config or make_config()
    command = SelectCommand(service)
    command._config = config or make_config()
    return command, service


class TestAssortInvalidRepos:
    def test_valid_repos_go_to_visible_repos(self):
        command, _ = make_command()
        valid = Repo(name='valid', path='/ok', git_info=GitInfo(valid=True))
        invalid = Repo(
            name='bad', path='/missing',
            git_info=GitInfo(valid=False, error='Path does not exist')
        )
        with patch.object(command, '_print_missing_paths_warning'):
            command._assort_invalid_repos([valid, invalid])
        assert len(command._visible_repos) == 1
        assert command._visible_repos[0].name == 'valid'

    def test_repos_with_path_error_excluded_from_visible(self):
        command, _ = make_command()
        invalid = Repo(
            name='bad', path='/missing',
            git_info=GitInfo(valid=False, error='Path does not exist')
        )
        with patch.object(command, '_print_missing_paths_warning'), \
             patch('git_repo_jumper.cli.commands.select.print_error'):
            command._assort_invalid_repos([invalid])
        assert command._visible_repos == []

    def test_warning_printed_for_invalid_repos(self):
        command, _ = make_command()
        invalid = Repo(
            name='bad', path='/missing',
            git_info=GitInfo(valid=False, error='Path does not exist')
        )
        with patch.object(command, '_print_missing_paths_warning') as mock_warn, \
             patch('git_repo_jumper.cli.commands.select.print_error'):
            command._assort_invalid_repos([invalid])
        mock_warn.assert_called_once()


class TestFormatFuzzyFinderChoice:
    def test_favorite_prefixed_with_star(self):
        command, _ = make_command()
        repo = Repo(
            name='myrepo', path='/p', fav=True,
            git_info=GitInfo(
                valid=True, current_branch_name='main',
                status='✓', github_repo_name='user/repo'
            ),
        )
        result = command._format_fuzzy_finder_choice(repo)
        assert result.startswith('★')

    def test_non_favorite_prefixed_with_spaces(self):
        command, _ = make_command()
        repo = Repo(
            name='myrepo', path='/p', fav=False,
            git_info=GitInfo(valid=True, current_branch_name='main'),
        )
        result = command._format_fuzzy_finder_choice(repo)
        assert result.startswith('  ')

    def test_no_git_info_uses_dashes(self):
        command, _ = make_command()
        repo = Repo(name='myrepo', path='/p', git_info=None)
        result = command._format_fuzzy_finder_choice(repo)
        assert '-' in result

    def test_contains_column_separator_pipes(self):
        command, _ = make_command()
        repo = Repo(
            name='myrepo', path='/p',
            git_info=GitInfo(valid=True, current_branch_name='main'),
        )
        result = command._format_fuzzy_finder_choice(repo)
        assert '│' in result


class TestCalculateMaxColumnWidths:
    def test_returns_max_name_length(self):
        command, _ = make_command()
        command._visible_repos = [
            Repo(
                name='short',
                path='/a',
                git_info=GitInfo(valid=True)
            ),
            Repo(
                name='a-much-longer-name',
                path='/b',
                git_info=GitInfo(valid=True)
            ),
        ]
        widths = command._calculate_max_column_widths()
        assert widths['name'] == len('a-much-longer-name')

    def test_returns_max_branch_length(self):
        command, _ = make_command()
        command._visible_repos = [
            Repo(
                name='r', path='/a',
                git_info=GitInfo(valid=True, current_branch_name='main'),
            ),
            Repo(
                name='s', path='/b',
                git_info=GitInfo(
                    valid=True, current_branch_name='feature/very-long-branch'
                ),
            ),
]
        widths = command._calculate_max_column_widths()
        assert widths['current_branch_name'] == len('feature/very-long-branch')

    def test_returns_zeros_for_empty_repo_list(self):
        command, _ = make_command()
        command._visible_repos = []
        widths = command._calculate_max_column_widths()
        assert all(v == 0 for v in widths.values())


class TestGetDateOfCachedData:
    def test_returns_unknown_when_date_is_none(self):
        command, service = make_command()
        service.date_cached_git_infos = None
        result = command._get_date_of_cached_data()
        assert result == '[unknown]'

    def test_returns_invalid_date_for_unparseable_string(self):
        command, service = make_command()
        service.date_cached_git_infos = 'not-a-date'
        result = command._get_date_of_cached_data()
        assert result == '[invalid date]'

    def test_shows_minutes_ago_for_recent_cache(self):
        command, service = make_command()
        five_min_ago = (
            datetime.now().astimezone() - timedelta(minutes=5)
        ).isoformat()
        service.date_cached_git_infos = five_min_ago
        result = command._get_date_of_cached_data()
        assert 'min ago' in result

    def test_shows_hours_ago_for_older_cache(self):
        command, service = make_command()
        two_hours_ago = (
            datetime.now().astimezone() - timedelta(hours=2)
        ).isoformat()
        service.date_cached_git_infos = two_hours_ago
        result = command._get_date_of_cached_data()
        assert 'h ago' in result

    def test_shows_days_ago_for_old_cache(self):
        command, service = make_command()
        three_days_ago = (
            datetime.now().astimezone() - timedelta(days=3)
        ).isoformat()
        service.date_cached_git_infos = three_days_ago
        result = command._get_date_of_cached_data()
        assert 'd ago' in result


class TestHandleSelectedRepo:
    def test_prints_warning_when_selection_is_none(self):
        command, _ = make_command()
        command._visible_repos = [Repo(name='r', path='/p')]
        command._cd_only = False
        with patch(
            'git_repo_jumper.cli.commands.select.print_warning'
        ) as mock_warn:
            command._handle_selected_repo(None)
        mock_warn.assert_called_once()

    def test_prints_warning_when_index_out_of_range(self):
        command, _ = make_command()
        command._visible_repos = [Repo(name='r', path='/p')]
        command._cd_only = False
        with patch(
            'git_repo_jumper.cli.commands.select.print_warning'
        ) as mock_warn:
            command._handle_selected_repo(99)
        mock_warn.assert_called_once()

    def test_prints_warning_when_negative_index(self):
        command, _ = make_command()
        command._visible_repos = [Repo(name='r', path='/p')]
        command._cd_only = False
        with patch(
            'git_repo_jumper.cli.commands.select.print_warning'
        ) as mock_warn:
            command._handle_selected_repo(-1)
        mock_warn.assert_called_once()


class TestRunErrorHandling:
    def test_prints_error_on_config_not_found(self):
        service = MagicMock()
        service.get_config.side_effect = ConfigNotFoundError(
            Path('/missing.yaml')
        )
        command = SelectCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.select.print_error'
        ) as mock_error:
            command.run()
        mock_error.assert_called_once()

    def test_prints_error_on_config_parse_error(self):
        service = MagicMock()
        service.get_config.side_effect = ConfigParseError(
            Path('/bad.yaml'), 'bad syntax'
        )
        command = SelectCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.select.print_error'
        ) as mock_error:
            command.run()
        mock_error.assert_called_once()

    def test_prints_error_on_unexpected_exception(self):
        service = MagicMock()
        service.get_config.side_effect = RuntimeError('unexpected')
        command = SelectCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.select.print_error'
        ) as mock_error:
            command.run()
        mock_error.assert_called_once()
