from pathlib import Path
from git_repo_jumper.domain.models import (
    Repo, Config, RepoSelectorColumnWidths, GitInfo
)


class TestRepoSelectorColumnWidths:
    def test_total_returns_sum_of_all_columns(self):
        widths = RepoSelectorColumnWidths(
            name=10, current_branch_name=15, status=8, github_repo_name=20
        )
        assert widths.total() == 53

    def test_total_with_default_values(self):
        widths = RepoSelectorColumnWidths()
        expected = (
            widths.name
            + widths.current_branch_name
            + widths.status
            + widths.github_repo_name
        )
        assert widths.total() == expected


class TestGitInfo:
    def test_github_repo_display_returns_name_when_set(self):
        info = GitInfo(valid=True, github_repo_name='owner/repo')
        assert info.github_repo_display == 'owner/repo'

    def test_github_repo_display_returns_dash_when_none(self):
        info = GitInfo(valid=True, github_repo_name=None)
        assert info.github_repo_display == '-'

    def test_invalid_factory_sets_valid_false(self):
        info = GitInfo.invalid('some error')
        assert info.valid is False

    def test_invalid_factory_sets_error_message(self):
        info = GitInfo.invalid('some error')
        assert info.error == 'some error'

    def test_invalid_factory_leaves_other_fields_none(self):
        info = GitInfo.invalid('err')
        assert info.current_branch_name is None
        assert info.status is None
        assert info.changes is None
        assert info.github_repo_name is None

    def test_default_valid_is_false(self):
        info = GitInfo()
        assert info.valid is False

    def test_default_all_fields_none(self):
        info = GitInfo()
        assert info.error is None
        assert info.current_branch_name is None
        assert info.status is None
        assert info.changes is None
        assert info.github_repo_name is None


class TestRepo:
    def test_show_defaults_to_true(self):
        repo = Repo(name='myrepo', path='/some/path')
        assert repo.show is True

    def test_fav_defaults_to_false(self):
        repo = Repo(name='myrepo', path='/some/path')
        assert repo.fav is False

    def test_git_info_defaults_to_none(self):
        repo = Repo(name='myrepo', path='/some/path')
        assert repo.git_info is None

    def test_custom_show_and_fav(self):
        repo = Repo(name='myrepo', path='/some/path', show=False, fav=True)
        assert repo.show is False
        assert repo.fav is True
