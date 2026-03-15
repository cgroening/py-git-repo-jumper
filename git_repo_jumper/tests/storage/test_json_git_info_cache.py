import json
import pytest
from git_repo_jumper.storage.git_info_cache.json import (
    JsonGitInfoCache, CACHE_FILE_NAME
)
from git_repo_jumper.domain.models import GitInfo
from git_repo_jumper.domain.errors import GitInfoCacheError


class TestSetStorageParentPath:
    def test_creates_cache_file_when_not_present(self, tmp_path):
        cache = JsonGitInfoCache()
        cache.set_storage_parent_path(tmp_path)
        assert (tmp_path / CACHE_FILE_NAME).exists()

    def test_does_nothing_when_path_is_none(self):
        cache = JsonGitInfoCache()
        cache.set_storage_parent_path(None)  # Must not raise

    def test_raises_git_info_cache_error_when_dir_missing(self):
        cache = JsonGitInfoCache()
        with pytest.raises(GitInfoCacheError):
            cache.set_storage_parent_path(
                '/nonexistent/dir/that/cannot/be/created'
            )


class TestSaveGitInfo:
    def test_writes_date_to_json(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        git_info = GitInfo(
            valid=True, current_branch_name='main', status='✓', changes=0
        )
        cache.save_git_info({'/repo': git_info}, '2026-03-15T10:00:00')
        data = json.loads((tmp_path / CACHE_FILE_NAME).read_text())
        assert data['date_and_time'] == '2026-03-15T10:00:00'

    def test_writes_repo_path_to_json(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        git_info = GitInfo(valid=True, current_branch_name='main')
        cache.save_git_info({'/repo/path': git_info}, '2026-03-15T10:00:00')
        data = json.loads((tmp_path / CACHE_FILE_NAME).read_text())
        assert data['repos'][0]['path'] == '/repo/path'

    def test_writes_branch_name_to_json(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        git_info = GitInfo(valid=True, current_branch_name='dev')
        cache.save_git_info({'/repo': git_info}, '2026-03-15T10:00:00')
        data = json.loads((tmp_path / CACHE_FILE_NAME).read_text())
        assert data['repos'][0]['git_info']['current_branch'] == 'dev'


class TestGetGitInfo:
    def test_returns_none_when_cache_file_missing(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        (tmp_path / CACHE_FILE_NAME).unlink()
        assert cache.get_git_info() is None

    def test_returns_date_string(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        git_info = GitInfo(
            valid=True, current_branch_name='main', status='✓', changes=0
        )
        cache.save_git_info({'/repo': git_info}, '2026-01-01T00:00:00')
        date, _ = cache.get_git_info()
        assert date == '2026-01-01T00:00:00'

    def test_returns_git_info_for_saved_repo(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        git_info = GitInfo(
            valid=True, error=None, current_branch_name='main',
            status='✓', changes=0, github_repo_name='user/repo'
        )
        cache.save_git_info({'/repo/path': git_info}, '2026-01-01T00:00:00')
        _, git_infos = cache.get_git_info()
        assert '/repo/path' in git_infos
        assert git_infos['/repo/path'].current_branch_name == 'main'
        assert git_infos['/repo/path'].valid is True

    def test_roundtrip_preserves_all_fields(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        original = GitInfo(
            valid=True, error=None, current_branch_name='feature/x',
            status='≠2', changes=2, github_repo_name='user/myrepo'
        )
        cache.save_git_info({'/repo': original}, '2026-01-01T00:00:00')
        _, git_infos = cache.get_git_info()
        result = git_infos['/repo']
        assert result.valid == original.valid
        assert result.current_branch_name == original.current_branch_name
        assert result.status == original.status
        assert result.changes == original.changes
        assert result.github_repo_name == original.github_repo_name

    def test_saves_and_retrieves_multiple_repos(self, tmp_path):
        cache = JsonGitInfoCache(tmp_path)
        git_infos = {
            '/repo/a': GitInfo(valid=True, current_branch_name='main'),
            '/repo/b': GitInfo(valid=False, error='Not a git repo'),
        }
        cache.save_git_info(git_infos, '2026-01-01T00:00:00')
        _, result = cache.get_git_info()
        assert len(result) == 2
        assert result['/repo/a'].current_branch_name == 'main'
        assert result['/repo/b'].valid is False
