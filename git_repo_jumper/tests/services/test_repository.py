import pytest
from pathlib import Path
from unittest.mock import MagicMock
from git_repo_jumper.services.repository import GitRepoService
from git_repo_jumper.domain.models import (
    Config, Repo, GitInfo, RepoSelectorColumnWidths
)
from git_repo_jumper.domain.errors import (
    SelectedRepoPathSaveError, GitInfoCacheError
)


def make_config(repos=None):
    return Config(
        config_path=Path('/fake/config.yaml'),
        repo_selector_column_widths=RepoSelectorColumnWidths(),
        git_tool_name='lazygit',
        github_username='testuser',
        repos=repos if repos is not None else [],
    )


def make_service(config=None):
    config_storage = MagicMock()
    config_storage.load_config.return_value = config or make_config()
    git_client = MagicMock()
    git_info_storage = MagicMock()
    git_info_storage.get_git_info.return_value = None
    service = GitRepoService(config_storage, git_client, git_info_storage)
    return service, config_storage, git_client, git_info_storage


class TestGetConfig:
    def test_loads_config_from_storage_on_first_call(self):
        service, config_storage, _, _ = make_service()
        config = service.get_config()
        config_storage.load_config.assert_called_once()
        assert config.git_tool_name == 'lazygit'

    def test_returns_cached_config_on_second_call(self):
        service, config_storage, _, _ = make_service()
        service.get_config()
        service.get_config()
        config_storage.load_config.assert_called_once()


class TestCachedGitInfosAvailable:
    def test_returns_false_when_cache_is_none(self):
        service, _, _, git_info_storage = make_service()
        git_info_storage.get_git_info.return_value = None
        assert service.cached_git_infos_available() is False

    def test_returns_false_when_cache_dict_is_empty(self):
        service, _, _, git_info_storage = make_service()
        git_info_storage.get_git_info.return_value = (None, {})
        assert service.cached_git_infos_available() is False

    def test_returns_true_when_cache_has_data(self):
        service, _, _, git_info_storage = make_service()
        git_info_storage.get_git_info.return_value = (
            '2026-03-15T10:00:00+01:00',
            {'/path/to/repo': GitInfo(valid=True)},
        )
        assert service.cached_git_infos_available() is True

    def test_returns_false_when_exception_raised(self):
        service, _, _, git_info_storage = make_service()
        git_info_storage.get_git_info.side_effect = Exception('fail')
        assert service.cached_git_infos_available() is False


class TestGetVisibleRepos:
    def test_filters_out_hidden_repos(self):
        repos = [
            Repo(name='visible', path='/a', show=True),
            Repo(name='hidden', path='/b', show=False),
        ]
        service, _, _, _ = make_service(make_config(repos))
        result = service._get_visible_repos()
        assert len(result) == 1
        assert result[0].name == 'visible'

    def test_sorts_favorites_before_non_favorites(self):
        repos = [
            Repo(name='alpha', path='/a', fav=False),
            Repo(name='beta', path='/b', fav=True),
        ]
        service, _, _, _ = make_service(make_config(repos))
        result = service._get_visible_repos()
        assert result[0].name == 'beta'

    def test_sorts_non_favorites_alphabetically(self):
        repos = [
            Repo(name='Zebra', path='/z'),
            Repo(name='apple', path='/a'),
            Repo(name='Mango', path='/m'),
        ]
        service, _, _, _ = make_service(make_config(repos))
        result = service._get_visible_repos()
        names = [r.name for r in result]
        assert names == sorted(names, key=str.lower)

    def test_returns_empty_list_when_no_repos(self):
        service, _, _, _ = make_service(make_config([]))
        assert service._get_visible_repos() == []


class TestStoreSelectedRepoPath:
    def test_writes_repo_path_to_file(self, tmp_path):
        config = Config(
            config_path=tmp_path / 'config.yaml',
            repo_selector_column_widths=RepoSelectorColumnWidths(),
            git_tool_name=None,
            github_username=None,
            repos=[],
        )
        service, _, _, _ = make_service(config)
        service.store_selected_repo_path('/my/repo')
        saved = (tmp_path / 'selected-repo.txt').read_text()
        assert saved == '/my/repo'

    def test_raises_selected_repo_path_save_error_on_failure(self):
        config = Config(
            config_path=Path('/nonexistent/dir/config.yaml'),
            repo_selector_column_widths=RepoSelectorColumnWidths(),
            git_tool_name=None,
            github_username=None,
            repos=[],
        )
        service, _, _, _ = make_service(config)
        with pytest.raises(SelectedRepoPathSaveError):
            service.store_selected_repo_path('/my/repo')


class TestAddCachedGitStatusToRepos:
    def test_assigns_git_info_from_cache(self):
        repo = Repo(name='r', path='/repo')
        git_info = GitInfo(valid=True, current_branch_name='main')
        cache = ('2026-01-01T00:00:00', {'/repo': git_info})
        service, _, _, _ = make_service()
        service._add_cached_git_status_to_repos([repo], cache)
        assert repo.git_info == git_info

    def test_stores_cache_date(self):
        repo = Repo(name='r', path='/repo')
        cache = ('2026-01-01T12:00:00', {'/repo': GitInfo(valid=True)})
        service, _, _, _ = make_service()
        service._add_cached_git_status_to_repos([repo], cache)
        assert service.date_cached_git_infos == '2026-01-01T12:00:00'

    def test_leaves_git_info_none_for_unknown_path(self):
        repo = Repo(name='r', path='/other')
        cache = ('2026-01-01T00:00:00', {'/repo': GitInfo(valid=True)})
        service, _, _, _ = make_service()
        service._add_cached_git_status_to_repos([repo], cache)
        assert repo.git_info is None


class TestGetVisibleReposWithGitStatus:
    def test_raises_git_info_cache_error_when_storage_raises(self):
        service, _, _, git_info_storage = make_service()
        git_info_storage.set_storage_parent_path.side_effect = Exception('boom')
        with pytest.raises(GitInfoCacheError):
            service.get_visible_repos_with_git_status()

    def test_uses_cached_data_when_flag_is_set(self):
        repo = Repo(name='r', path='/repo')
        git_info = GitInfo(valid=True, current_branch_name='main')
        service, _, _, git_info_storage = make_service(make_config([repo]))
        git_info_storage.get_git_info.return_value = (
            '2026-01-01T00:00:00', {'/repo': git_info}
        )
        result = service.get_visible_repos_with_git_status(use_cached_data=True)
        assert result[0].git_info == git_info

    def test_fetches_live_data_when_flag_not_set(self):
        repo = Repo(name='r', path='/repo')
        live_info = GitInfo(valid=True, current_branch_name='dev')
        service, _, git_client, git_info_storage = make_service(
            make_config([repo])
        )
        git_info_storage.get_git_info.return_value = None
        git_client.get_git_status.return_value = live_info
        result = service.get_visible_repos_with_git_status(use_cached_data=False)
        assert result[0].git_info == live_info
