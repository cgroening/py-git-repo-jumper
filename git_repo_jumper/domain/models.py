from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class Repo:
    """
    Repository information from config.

    Attributes:
    -----------
    name : str
        Repository name (can be derived from path if missing).
    path : str
        Repository path.
    show : bool
        Whether to show this repository in the list (default True).
    fav : bool
        Whether this repository is a favorite (default False).
    """
    name: str
    path: str
    show: bool = True
    fav: bool = False


@dataclass(slots=True, frozen=True)
class Config:
    """
    Configuration data for git-repo-jumper.
    """
    config_path: Path
    git_tool_name: str | None
    github_username: str | None
    repos: list[Repo] | None


@dataclass(slots=True, frozen=True)
class GitStatus:
    """
    Git status information for a repository.

    Attributes:
    -----------
    valid : bool
        Whether the repository path is valid.
    error : str | None
        Error message if invalid, else None.
    branch : str
        Current branch name.
    status : str
        Status summary (clean, changes, ahead/behind).
    changes : int
        Number of uncommitted changes.
    github_repo : str
        GitHub repository name or "-".
    """
    valid: bool
    error: str | None
    branch: str
    status: str
    changes: int
    github_repo: str


@dataclass(slots=True, frozen=True)
class RepoWithStatus:
    """
    Repository name + path with its git status.

    Attributes:
    -----------
    name : str
        Repository name.
    path : str
        Repository path.
    git_info : GitStatus
        Git status information.
    """
    name : str
    path : str
    git_info: GitStatus
