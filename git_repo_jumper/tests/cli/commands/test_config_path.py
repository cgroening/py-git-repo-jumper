from pathlib import Path
from unittest.mock import MagicMock, patch
from git_repo_jumper.cli.commands.config_path import ConfigPathCommand
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.domain.models import Config, RepoSelectorColumnWidths


def make_config():
    return Config(
        config_path=Path('/fake/config.yaml'),
        repo_selector_column_widths=RepoSelectorColumnWidths(),
        git_tool_name=None,
        github_username=None,
        repos=[],
    )


class TestConfigPathCommandRun:
    def setup_method(self):
        self.service = MagicMock()
        self.command = ConfigPathCommand(self.service)

    def test_displays_config_path_on_success(self):
        self.service.get_config.return_value = make_config()

        with patch(
            'git_repo_jumper.cli.commands.config_path.print_custom_panel'
        ) as mock_panel:
            self.command.run()
            mock_panel.assert_called_once()
            assert '/fake/config.yaml' in str(mock_panel.call_args)

    def test_prints_error_on_config_not_found(self):
        """
        Test that the command prints an error message  `ConfigNotFoundError`
        is raised. The specified path in this test is irrelevant because the
        focus is on the error handling.
        """
        self.service.get_config.side_effect = ConfigNotFoundError(Path('/'))

        with patch(
            'git_repo_jumper.cli.commands.config_path.print_error'
        ) as mock_error:
            self.command.run()
            mock_error.assert_called_once()

    def test_prints_error_on_config_parse_error(self):
        self.service.get_config.side_effect = ConfigParseError(
            Path('/'), 'syntax error'
        )
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_error'
        ) as mock_error:
            self.command.run()
            mock_error.assert_called_once()

    def test_prints_error_on_unexpected_exception(self):
        self.service.get_config.side_effect = RuntimeError('unexpected')
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_error'
        ) as mock_error:
            self.command.run()
            mock_error.assert_called_once()


class TestDisplayConfigPath:
    def test_calls_print_custom_panel(self):
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_custom_panel'
        ) as mock_panel:
            ConfigPathCommand._display_config_path(Path('/some/config.yaml'))
            mock_panel.assert_called_once()

    def test_panel_contains_config_path(self):
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_custom_panel'
        ) as mock_panel:
            ConfigPathCommand._display_config_path(Path('/some/config.yaml'))
            assert '/some/config.yaml' in str(mock_panel.call_args)
