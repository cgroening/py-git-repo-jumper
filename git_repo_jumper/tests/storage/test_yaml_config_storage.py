import pytest
from pathlib import Path
from git_repo_jumper.storage.config.yaml_config_storage import YamlConfigStorage
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.domain.models import RepoSelectorColumnWidths


class TestYamlConfigStorageLoadConfig:
    def test_raises_config_not_found_error_when_file_missing(self, tmp_path):
        storage = YamlConfigStorage(tmp_path / 'nonexistent.yaml')
        with pytest.raises(ConfigNotFoundError):
            storage.load_config()

    def test_raises_config_parse_error_on_invalid_yaml(self, tmp_path):
        config_file = tmp_path / 'config.yaml'
        config_file.write_text('key: [unclosed bracket')
        storage = YamlConfigStorage(config_file)
        with pytest.raises(ConfigParseError):
            storage.load_config()

    def test_loads_git_tool_and_github_username(self, tmp_path):
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'git-program: lazygit\n'
            'github-username: testuser\n'
        )
        storage = YamlConfigStorage(config_file)
        config = storage.load_config()
        assert config.git_tool_name == 'lazygit'
        assert config.github_username == 'testuser'

    def test_loads_repos(self, tmp_path):
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'repos:\n'
            '  - name: myrepo\n'
            '    path: /some/path\n'
        )
        storage = YamlConfigStorage(config_file)
        config = storage.load_config()
        assert config.repos is not None
        assert len(config.repos) == 1
        assert config.repos[0].name == 'myrepo'

    def test_config_path_set_to_file(self, tmp_path):
        config_file = tmp_path / 'config.yaml'
        config_file.write_text('git-program: lazygit\n')
        storage = YamlConfigStorage(config_file)
        config = storage.load_config()
        assert config.config_path == config_file

    def test_uses_default_config_path_when_none_given(self):
        storage = YamlConfigStorage(None)
        assert 'git-repo-jumper' in str(storage._config_path)


class TestParseRepos:
    def test_returns_none_for_none_input(self):
        assert YamlConfigStorage._parse_repos(None) is None

    def test_returns_none_for_non_list_input(self):
        assert YamlConfigStorage._parse_repos('not a list') is None

    def test_skips_entries_without_path(self):
        result = YamlConfigStorage._parse_repos([{'name': 'nope'}])
        assert result == []

    def test_uses_folder_name_when_name_missing(self):
        result = YamlConfigStorage._parse_repos([{'path': '/home/user/myproject'}])
        assert result is not None
        assert result[0].name == 'myproject'

    def test_parses_show_and_fav_flags(self):
        repos_raw = [{'path': '/some/path', 'name': 'r', 'show': False, 'fav': True}]
        result = YamlConfigStorage._parse_repos(repos_raw)
        assert result is not None
        assert result[0].show is False
        assert result[0].fav is True

    def test_defaults_show_true_fav_false(self):
        result = YamlConfigStorage._parse_repos([{'path': '/some/path', 'name': 'r'}])
        assert result is not None
        assert result[0].show is True
        assert result[0].fav is False


class TestParseRepoSelectorColumnWidths:
    def test_returns_defaults_for_none_input(self):
        result = YamlConfigStorage._parse_repo_selector_column_widths(None)
        assert isinstance(result, RepoSelectorColumnWidths)

    def test_returns_defaults_for_non_dict_input(self):
        result = YamlConfigStorage._parse_repo_selector_column_widths('bad')
        assert isinstance(result, RepoSelectorColumnWidths)

    def test_parses_custom_name_width(self):
        result = YamlConfigStorage._parse_repo_selector_column_widths({'name': 30})
        assert result.name == 30

    def test_parses_custom_status_width(self):
        result = YamlConfigStorage._parse_repo_selector_column_widths({'status': 12})
        assert result.status == 12

    def test_uses_defaults_for_unspecified_columns(self):
        defaults = RepoSelectorColumnWidths()
        result = YamlConfigStorage._parse_repo_selector_column_widths({'name': 30})
        assert result.current_branch_name == defaults.current_branch_name
        assert result.github_repo_name == defaults.github_repo_name
