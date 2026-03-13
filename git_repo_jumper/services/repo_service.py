import subprocess
from pathlib import Path
from datetime import datetime
from git_repo_jumper.domain.errors import (
    SelectedRepoPathSaveError, ConfiguredGitToolNotFoundError,
    GitInfoCacheError
)
from git_repo_jumper.domain.models import Config, GitInfo, Repo
from git_repo_jumper.storage.config_storage import ConfigStorage
from git_repo_jumper.storage.git_info_storage import GitInfoStorage


class GitRepoService:
    """
    Service layer for managing and interacting with Git repositories.

    Loads repository configurations via `ConfigStorage` and provides methods
    to query git status, filter and sort repositories, open them in external
    git tools and persist the last selected repository path for shell
    integration.

    Attributes:
    -----------
    _storage : ConfigStorage
        Storage backend used to load the configuration.
    _config : Config | None
        Cached configuration object, loaded lazily on first access.
    """
    _config_storage: ConfigStorage
    _git_info_cache_storage: GitInfoStorage
    _config: Config | None = None
    _date_cached_git_infos: str | None = None


    @property
    def date_cached_git_infos(self) -> str | None:
        return self._date_cached_git_infos


    def __init__(
        self, config_storage: ConfigStorage, git_info_storage: GitInfoStorage
    ) -> None:
        """Saves the provided storage instance."""
        self._config_storage = config_storage
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

    def get_visible_repos_with_git_status(
        self, do_fetch: bool = False, use_cached_data: bool = False
    ) -> list[Repo]:
        """
        Returns a list of all repos not configured as hidden including git
        status information if they coule be retrieved (from cache or by
        running git).
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

        # Retrieve git status information from cache or by running git commands,
        # depending on the `use_cached_data` flag and cache availability
        if use_cached_data and git_info_cache:
            self._add_cached_git_status_to_repos(repos, git_info_cache)
        else:
            repos = self._add_current_git_status_to_repos(repos, do_fetch)

        return repos

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
            self, repos: list[Repo], do_fetch: bool = False
    ) -> list[Repo]:
        """
        Adds the current git status information to each repository in the
        given list.
        """
        git_infos: dict[str, GitInfo] = {}
        for repo in repos:
            repo.git_info = self._get_git_status(
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

    @staticmethod
    def _get_git_status(
        repo_path: str, github_username: str | None, do_fetch: bool = False
    ) -> GitInfo:
        """
        Determines the git status of a repository.

        Parameters:
        -----------
        repo_path : str
            Path to the repository.
        github_username : str
            GitHub username to use when extracting repo name.

        Returns:
        --------
        GitStatus
            A GitStatus object containing `valid` (`bool`),
            `error` (`str | None`), `branch` (`str`), `status (`str`),
            `changes` (`int`) and `github_repo_name` (`str`).
        """
        # Validate path and .git directory existence
        path = Path(repo_path).expanduser()

        if not path.exists():
           return GitInfo.invalid('Path does not exist')

        if not (path / '.git').exists():
           return GitInfo.invalid('Not a git repository')

        # Get git information using subprocess calls
        try:
            GitRepoService._fetch_latest_changes(path, do_fetch)
            current_branch_name = GitRepoService._get_current_branch_name(path)
            status_text, changes = GitRepoService._generate_status_summary(path)
            github_repo_name = GitRepoService._get_github_repo_name(
                repo_path, github_username or ''
            )

            return GitInfo(
                valid=True,
                error=None,
                current_branch_name=current_branch_name,
                status=status_text,
                changes=changes,
                github_repo_name=github_repo_name
            )

        except subprocess.TimeoutExpired:
           return GitInfo.invalid('Timeout')

        except Exception as e:
           return GitInfo.invalid(str(e))

    @staticmethod
    def _fetch_latest_changes(path: Path, do_fetch: bool) -> None:
        """Fetch latest changes from remote to get ahead/behind status."""
        if not do_fetch:
            return

        try:
            subprocess.run(
                ['git', '-C', str(path), 'fetch', '--quiet'],
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            pass

    @staticmethod
    def _get_current_branch_name(path: Path) -> str:
        """
        Return the current branch name of the git repository at the given path.
        """
        branch_result = subprocess.run(
            ['git', '-C', str(path), 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, timeout=5
        )
        return (
            branch_result.stdout.strip()
            if branch_result.returncode == 0 else '[unknown]'
        )

    @staticmethod
    def _generate_status_summary(path: Path) -> tuple[str, int]:
        """
        Generates a status summary string and the number of changes for the
        repository at the given path.
        """
        status_result = subprocess.run(
            ['git', '-C', str(path), 'status', '--porcelain'],
            capture_output=True, text=True, timeout=5
        )
        changes = (len(status_result.stdout.strip().split('\n'))
                   if status_result.stdout.strip() else 0)

        upstream_result = subprocess.run(
            ['git', '-C', str(path), 'rev-list', '--count', '--left-right',
             '@{upstream}...HEAD'],
            capture_output=True, text=True, timeout=5
        )

        behind, ahead = 0, 0
        if upstream_result.returncode == 0:
            parts = upstream_result.stdout.strip().split()
            behind, ahead = int(parts[0]), int(parts[1])

        status_parts = []
        if changes > 0:
            status_parts.append(f'≠{changes}')
        if behind > 0:
            status_parts.append(f'↓{behind}')
        if ahead > 0:
            status_parts.append(f'↑{ahead}')

        status_text = ' '.join(status_parts) if status_parts else '✓'


        return status_text, changes

    @staticmethod
    def _get_github_repo_name(repo_path: str, github_username: str = "") -> str:
        """
        Extracts the GitHub repository name from git remote URL.

        Parameters:
        -----------
        repo_path : str
            Path to the remote repository.
        github_username : str
            GitHub username to remove from the repo name if present.

        Returns:
        --------
        str
            GitHub repository name in "owner/repo" format or "-" if not found.
        """
        path = Path(repo_path).expanduser()

        if not (path / ".git").exists():
            return "-"

        try:
            # Get remote URL
            remote_result = subprocess.run(
                ["git", "-C", str(path), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5
            )

            if remote_result.returncode != 0:
                return "-"

            remote_url = remote_result.stdout.strip()

            # Parse GitHub URL (both HTTPS and SSH formats)
            # HTTPS: https://github.com/user/repo.git
            # SSH: git@github.com:user/repo.git
            if "github.com" not in remote_url:
                return "-"

            # Extract owner/repo
            if remote_url.startswith("git@github.com:"):
                # SSH format: git@github.com:user/repo.git
                repo_part = remote_url.replace("git@github.com:", "")
            elif "github.com/" in remote_url:
                # HTTPS format: https://github.com/user/repo.git
                repo_part = remote_url.split("github.com/")[1]
            else:
                return "-"

            # Remove .git suffix if present
            repo_part = repo_part.replace(".git", "")

            # Remove GitHub username from path if present
            repo_part = repo_part.replace(f"{github_username}/", "")

            return repo_part

        except (subprocess.TimeoutExpired, Exception):
            return "-"

    def store_selected_repo_path(self, repo_path: str) -> None:
        """
        Stores the path of the selected repository in a file named
        `selected-repo.txt` in the same directory as the config file.
        This allows external tools (e.g. a shell function) to read the path of
        the last opened repository after the git program exits and change the
        current directory of the terminal to that path.

        Parameters:
        -----------
        repo_path : str
            The path of the repository to store.

        Raises:
        -------
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

    @staticmethod
    def open_git_tool(repo_path: str, git_program: str) -> None:
        """
        Opens the repository in the specified git program.

        Parameters:
        -----------
        repo_path : str
            Path to the repository.
        git_program : str
            Git program to use (e.g., lazygit, gitui, tig).

        Raises:
        -------
        ConfiguredGitToolNotFoundError
            If the specified git program is not found or fails to open.
        """
        path = Path(repo_path).expanduser()

        # Program-specific commands
        commands = {
            'lazygit': ['lazygit', '-p', str(path)],
            'gitui': ['gitui', '-d', str(path)],
            'tig': ['tig', '-C', str(path)],
            'gh': ['gh', 'repo', 'view', '--web']
        }

        # Use custom command if provided, otherwise use known commands
        if git_program in commands:
            cmd = commands[git_program]
        else:
            # For unknown programs, assume they accept -p flag
            cmd = [git_program, '-p', str(path)]

        try:
            # Special handling for gh (needs to run from within the repo)
            if git_program == 'gh':
                subprocess.run(cmd, cwd=str(path), check=True)
            else:
                subprocess.run(cmd, check=True)
        except FileNotFoundError:
            raise ConfiguredGitToolNotFoundError(git_program)
        except subprocess.CalledProcessError as e:
            raise ConfiguredGitToolNotFoundError(git_program, str(e))
