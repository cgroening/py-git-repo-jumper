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
    def test_displays_config_path_on_success(self):
        service = MagicMock()
        service.get_config.return_value = make_config()
        command = ConfigPathCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_custom_panel'
        ) as mock_panel:
            command.run()
            mock_panel.assert_called_once()
            assert '/fake/config.yaml' in str(mock_panel.call_args)

    def test_prints_error_on_config_not_found(self):
        service = MagicMock()
        service.get_config.side_effect = ConfigNotFoundError(Path('/missing.yaml'))
        command = ConfigPathCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_error'
        ) as mock_error:
            command.run()
            mock_error.assert_called_once()

    def test_prints_error_on_config_parse_error(self):
        service = MagicMock()
        service.get_config.side_effect = ConfigParseError(Path('/bad.yaml'), 'syntax error')
        command = ConfigPathCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_error'
        ) as mock_error:
            command.run()
            mock_error.assert_called_once()

    def test_prints_error_on_unexpected_exception(self):
        service = MagicMock()
        service.get_config.side_effect = RuntimeError('unexpected')
        command = ConfigPathCommand(service)
        with patch(
            'git_repo_jumper.cli.commands.config_path.print_error'
        ) as mock_error:
            command.run()
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
