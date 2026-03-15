from pathlib import Path
from git_repo_jumper.domain.errors import (
    ConfigNotFoundError, ConfigParseError, SelectedRepoPathSaveError,
    ConfiguredGitToolNotFoundError, GitInfoCacheError
)


class TestConfigNotFoundError:
    def test_is_exception(self):
        err = ConfigNotFoundError(Path('/some/path'))
        assert isinstance(err, Exception)

    def test_str_contains_path(self):
        err = ConfigNotFoundError(Path('/some/path/config.yaml'))
        assert '/some/path/config.yaml' in str(err)

    def test_str_says_not_found(self):
        err = ConfigNotFoundError(Path('/cfg.yaml'))
        assert 'not found' in str(err).lower()

    def test_message_passed_to_parent(self):
        err = ConfigNotFoundError(Path('/cfg.yaml'))
        assert err.args[0] == str(err)


class TestConfigParseError:
    def test_is_exception(self):
        err = ConfigParseError(Path('/cfg.yaml'), 'bad yaml')
        assert isinstance(err, Exception)

    def test_str_contains_path(self):
        err = ConfigParseError(Path('/cfg.yaml'), 'unexpected token')
        assert '/cfg.yaml' in str(err)

    def test_str_contains_error_message(self):
        err = ConfigParseError(Path('/cfg.yaml'), 'unexpected token')
        assert 'unexpected token' in str(err)

    def test_message_passed_to_parent(self):
        err = ConfigParseError(Path('/cfg.yaml'), 'msg')
        assert err.args[0] == str(err)


class TestSelectedRepoPathSaveError:
    def test_is_exception(self):
        err = SelectedRepoPathSaveError(
            '/tmp/selected-repo.txt', 'permission denied'
        )
        assert isinstance(err, Exception)

    def test_str_contains_file_path(self):
        err = SelectedRepoPathSaveError('/tmp/file.txt', 'disk full')
        assert '/tmp/file.txt' in str(err)

    def test_str_contains_error_message(self):
        err = SelectedRepoPathSaveError('/tmp/file.txt', 'disk full')
        assert 'disk full' in str(err)

    def test_message_passed_to_parent(self):
        err = SelectedRepoPathSaveError('/tmp/file.txt', 'msg')
        assert err.args[0] == str(err)


class TestConfiguredGitToolNotFoundError:
    def test_str_without_error_contains_tool_name(self):
        err = ConfiguredGitToolNotFoundError('lazygit')
        assert 'lazygit' in str(err)

    def test_str_without_error_says_not_found(self):
        err = ConfiguredGitToolNotFoundError('lazygit')
        assert 'not found' in str(err).lower()

    def test_str_with_error_contains_tool_name(self):
        err = ConfiguredGitToolNotFoundError('lazygit', 'command not found')
        assert 'lazygit' in str(err)

    def test_str_with_error_contains_error_message(self):
        err = ConfiguredGitToolNotFoundError('lazygit', 'command not found')
        assert 'command not found' in str(err)

    def test_message_passed_to_parent(self):
        err = ConfiguredGitToolNotFoundError('lazygit')
        assert err.args[0] == str(err)


class TestGitInfoCacheError:
    def test_str_without_error_contains_path(self):
        err = GitInfoCacheError(Path('/cache/path'))
        assert '/cache/path' in str(err)

    def test_str_with_error_contains_path(self):
        err = GitInfoCacheError(Path('/cache/path'), 'read error')
        assert '/cache/path' in str(err)

    def test_str_with_error_contains_error_message(self):
        err = GitInfoCacheError(Path('/cache/path'), 'read error')
        assert 'read error' in str(err)

    def test_message_passed_to_parent(self):
        err = GitInfoCacheError(Path('/cache/path'))
        assert err.args[0] == str(err)
