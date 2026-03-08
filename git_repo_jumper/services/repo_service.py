import subprocess
import sys
from pathlib import Path
from git_repo_jumper.domain.errors import SelectedRepoPathSaveError
from git_repo_jumper.domain.models import Config, GitInfo, Repo
from git_repo_jumper.storage.config_storage import ConfigStorage


class GitRepoService:
    _storage: ConfigStorage
    _config: Config | None


    def __init__(self, storage: ConfigStorage):
        self._storage = storage
        self._config = None

    def get_config(self) -> Config:
        if self._config:
            return self._config

        self._config = self._storage.load_config()
        return self._config

    def get_visible_repos(self) -> list[Repo]:
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
            self, do_fetch: bool = False
    ) -> list[Repo]:
        repos = self.get_visible_repos()
        for repo in repos:
            repo.git_info = self.get_git_status(
                repo.path, self.get_config().github_username, do_fetch
            )

        return repos

    # TODO: Clean-up this method and split into smaller methods
    @staticmethod
    def get_git_status(
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
            A GitStatus object containing:
            - valid (bool): Whether the path is a valid git repository.
            - error (str | None): Error message if invalid, else None.
            - branch (str): Current branch name.
            - status (str): Status summary (clean, changes, ahead/behind).
            - changes (int): Number of uncommitted changes.
            - github_repo (str): GitHub repository name or '-'.
        """

        path = Path(repo_path).expanduser()

        if not path.exists():
            return GitInfo(
                valid=False,
                error='Path does not exist',
                branch='',
                status='',
                changes=0,
                github_repo_name='-'
            )

        if not (path / '.git').exists():
            return GitInfo(
                valid=False,
                error='Not a git repository',
                branch='',
                status='',
                changes=0,
                github_repo_name='-'
            )

        try:
            branch_result = subprocess.run(
                ['git', '-C', str(path), 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=5
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'

            if do_fetch:
                try:
                    subprocess.run(
                        ['git', '-C', str(path), 'fetch', '--quiet'],
                        capture_output=True,
                        timeout=10,
                    )
                except subprocess.TimeoutExpired:
                    pass

            status_result = subprocess.run(
                ['git', '-C', str(path), 'status', '--porcelain'],
                capture_output=True, text=True, timeout=5
            )
            changes = len(status_result.stdout.strip().split('\n')) if status_result.stdout.strip() else 0

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
                status_parts.append(f'≠ {changes}')
            if behind > 0:
                status_parts.append(f'↓ {behind}')
            if ahead > 0:
                status_parts.append(f'↑ {ahead}')

            status_text = ' '.join(status_parts) if status_parts else '✓'

            github_repo = GitRepoService.get_github_repo_name(repo_path, github_username)

            return GitInfo(
                valid=True,
                error=None,
                branch=branch,
                status=status_text,
                changes=changes,
                github_repo_name=github_repo
            )

        except subprocess.TimeoutExpired:
            return GitInfo(
                valid=False,
                error='Timeout',
                branch='',
                status='',
                changes=0,
                github_repo_name='-'
            )

        except Exception as e:
            return GitInfo(
                valid=False,
                error=str(e),
                branch='',
                status='',
                changes=0,
                github_repo_name='-'
            )

    @staticmethod
    def get_github_repo_name(repo_path: str, github_username: str = "") -> str:
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
            # TODO: Handle this in list_.py
            console.print(f'[red]Error: {git_program} is not installed![/red]')
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            # TODO: Handle this in list_.py
            console.print(f'[red]Error opening {git_program}: {e}[/red]')
            sys.exit(1)
