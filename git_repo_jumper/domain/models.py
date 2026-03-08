from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
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
    git_status : GitStatus | None
        Git status information for this repository or None if not yet fetched.
    """
    name: str
    path: str
    show: bool = True
    fav: bool = False
    git_info: GitInfo | None = None


@dataclass(slots=True, frozen=True)
class Config:
    """
    Configuration data for git-repo-jumper.
    """
    config_path: Path
    repo_selector_column_widths: RepoSelectorColumnWidths
    git_tool_name: str | None
    github_username: str | None
    repos: list[Repo] | None


@dataclass(slots=True, frozen=True)
class RepoSelectorColumnWidths:
    """
    Maximum column widths for the repository selector UI (e.g. fuzzy finder).
    """
    name: int = 20
    branch: int = 15
    status: int = 10
    github_repo_name: int = 20


@dataclass(slots=True, frozen=True)
class GitInfo:
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
    github_repo_name : str
        GitHub repository name.
    """
    valid: bool = False
    error: str | None = None
    branch: str | None = None
    status: str | None = None
    changes: int | None = None
    github_repo_name: str | None = None

    @property
    def github_repo_display(self) -> str:
        return self.github_repo_name or '-'

