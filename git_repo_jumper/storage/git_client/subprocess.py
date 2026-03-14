import subprocess
from pathlib import Path
from git_repo_jumper.domain.models import GitInfo
from git_repo_jumper.domain.errors import ConfiguredGitToolNotFoundError
from git_repo_jumper.storage.git_client.base import BaseGitClient


class SubprocessGitClient(BaseGitClient):
    """Adapter to the Git CLI. Executes git commands via subprocess."""


    def get_git_status(
        self, repo_path: str, github_username: str | None, do_fetch: bool = False
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
            SubprocessGitClient._fetch_latest_changes(path, do_fetch)
            current_branch_name = SubprocessGitClient._get_current_branch_name(path)
            status_text, changes = SubprocessGitClient._generate_status_summary(path)
            github_repo_name = SubprocessGitClient._get_github_repo_name(
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


    def open_git_tool(self, repo_path: str, git_program: str) -> None:
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

