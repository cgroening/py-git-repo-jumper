from collections.abc import Callable
from datetime import datetime
from git_repo_jumper.domain.errors import (
    SelectedRepoPathSaveError, GitInfoCacheError
)
from git_repo_jumper.domain.models import Config, GitInfo, Repo
from git_repo_jumper.storage.config.config_storage import BaseConfigStorage
from git_repo_jumper.storage.git_client.base import BaseGitClient
from git_repo_jumper.storage.git_info_cache.base import BaseGitInfoCache


class GitRepoService:
    """
    Service layer for managing and interacting with Git repositories.

    Loads repository configurations via `ConfigStorage` and provides methods
    to query git status, filter and sort repositories, open them in external
    git tools and persist the last selected repository path for shell
    integration.
    """
    _config_storage: BaseConfigStorage
    _git_client: BaseGitClient
    _git_info_cache_storage: BaseGitInfoCache
    _config: Config | None = None
    _date_cached_git_infos: str | None = None


    @property
    def date_cached_git_infos(self) -> str | None:
        return self._date_cached_git_infos


    def __init__(
        self,
        config_storage: BaseConfigStorage,
        git_client: BaseGitClient,
        git_info_storage: BaseGitInfoCache,
    ) -> None:
        """Saves the provided storage instance."""
        self._config_storage = config_storage
        self._git_client = git_client
        self._git_info_cache_storage = git_info_storage

    def get_config(self) -> Config:
        """
        Returns the configuration object, loading it from storage if not already
        cached.
        """
        if self._config:
            return self._config

        self._config = self._config_storage.load_config()
        return self._config

    def cached_git_infos_available(self) -> bool:
        """Checks if cached git status data are available and not empty."""
        try:
            git_info_storage_parent_path = self.get_config().config_path.parent
            self._git_info_cache_storage.set_storage_parent_path(
                git_info_storage_parent_path
            )
            git_info_cache = self._git_info_cache_storage.get_git_info()
        except Exception:
            return False

        if not git_info_cache:
            return False

        date_cached_git_infos, cached_git_infos_dict = git_info_cache

        if date_cached_git_infos and cached_git_infos_dict:
            return True
        return False

    def get_visible_repos_with_git_status(
        self,
        do_fetch: bool = False,
        use_cached_data: bool = False,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> list[Repo]:
        """
        Returns a list of all repos not configured as hidden including git
        status information if they coule be retrieved (from cache or by
        running git).

        Raises
        ------
        GitInfoCacheError
            If there is an error accessing the git info cache.
        """
        repos: list[Repo] = self._get_visible_repos()
        git_info_storage_parent_path = self.get_config().config_path.parent
        git_info_cache = None

        # Get instance of GitInfoCacheStorage
        try:
            self._git_info_cache_storage.set_storage_parent_path(
               git_info_storage_parent_path
            )
            git_info_cache = self._git_info_cache_storage.get_git_info()
        except Exception as e:
            raise GitInfoCacheError(git_info_storage_parent_path, str(e))

        # Retrieve git status information from
        # - example data if in example mode,
        # - cache if `use_cached_data` is True and cache is available
        # - or by running git commands
        if self._config and self._config.example_mode:
            self._add_example_git_status_to_repos(repos)
        elif use_cached_data and git_info_cache:
            self._add_cached_git_status_to_repos(repos, git_info_cache)
        else:
            repos = self._add_current_git_status_to_repos(
                repos, do_fetch, on_progress
            )

        return repos

    def store_selected_repo_path(self, repo_path: str) -> None:
        """
        Stores the path of the selected repository in a file named
        `selected-repo.txt` in the same directory as the config file.
        This allows external tools (e.g. a shell function) to read the path of
        the last opened repository after the git program exits and change the
        current directory of the terminal to that path.

        Parameters
        ----------
        repo_path : str
            The path of the repository to store.

        Raises
        ------
        SelectedRepoPathSaveError
            If there is an error saving the repository path.
        """
        config_parent_path = self.get_config().config_path.parent
        selected_repo_path_file = config_parent_path / 'selected-repo.txt'

        try:
            with open(selected_repo_path_file, 'w') as f:
                f.write(repo_path)
        except Exception as e:
            raise SelectedRepoPathSaveError(str(selected_repo_path_file), str(e))

    def open_git_tool(self, repo_path: str, git_program: str) -> None:
        """Opens the specified repository in the configured git program."""
        self._git_client.open_git_tool(repo_path, git_program)

    def _get_visible_repos(self) -> list[Repo]:
        """
        Returns a list of repositories from the config file that are not
        marked as hidden (i.e. don't have `show: false`), sorted with
        favorites first and then alphabetically by name.
        """
        visible_repos: list[Repo] = []

        # Filter out hidden repositories
        for repo in self.get_config().repos or []:
            if not repo.show:
                continue
            visible_repos.append(repo)

        # Sort favorites first, then alphabetically by name (case-insensitive)
        visible_repos.sort(key=lambda r: (not r.fav, r.name.lower()))

        return visible_repos

    def _add_cached_git_status_to_repos(
        self,
        repos: list[Repo],
        git_info_cache:tuple[str | None, dict[str, GitInfo]]
    ) -> list[Repo]:
        """
        Adds cached git status information to each repository in the given
        list.
        """
        self._date_cached_git_infos, cached_git_infos_dict = git_info_cache

        if not cached_git_infos_dict:
            return repos

        for repo in repos:
            repo.git_info = cached_git_infos_dict.get(repo.path, None)

        return repos

    def _add_current_git_status_to_repos(
        self,
        repos: list[Repo],
        do_fetch: bool = False,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> list[Repo]:
        """
        Adds the current git status information to each repository in the
        given list.
        """
        git_infos: dict[str, GitInfo] = {}
        total = len(repos)
        for i, repo in enumerate(repos):
            if on_progress:
                on_progress(repo.name, i + 1, total)
            repo.git_info = self._git_client.get_git_status(
                repo.path, self.get_config().github_username, do_fetch
            )
            git_infos[repo.path] = repo.git_info

        # Save git infos in cache for optional later use
        try:
            self._git_info_cache_storage.save_git_info(
                git_infos,
                date_and_time_iso=datetime.now().astimezone().isoformat()
            )
        except Exception:
            pass  # Don't handle because error is handled when reading cache

        return repos

    def _add_example_git_status_to_repos(self, repos: list[Repo]) -> list[Repo]:
        """
        Sets the field `git_info` of each repository in the given list to the
        value of the field `example_git_info`. This is used in example mode to
        show example git status information without actually running git
        commands or reading from the cache.
        """
        for repo in repos:
            repo.git_info = repo.example_git_info

        return repos

