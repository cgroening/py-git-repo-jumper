from abc import ABC, abstractmethod
from pathlib import Path
from git_repo_jumper.domain.models import GitInfo


class BaseGitInfoCache(ABC):
    """
    Interface for caching and retrieving Git status information for
    Git repositories.
    """
    _storage_path: Path


    @abstractmethod
    def set_storage_parent_path(
        self, storage_parent_path: Path | str | None
    ) -> None:
        """Set the path to the configuration file if provided is not None."""
        ...

    @abstractmethod
    def save_git_info(
        self,
        git_infos: dict[str, GitInfo],
        date_and_time_iso: str
    ) -> None:
        """Stores the GitInfo for the given repository path."""
        ...

    @abstractmethod
    def get_git_info(self)-> tuple[str | None, dict[str, GitInfo]] | None:
        """
        Returns the GitInfo for the given repository path, or None if not found.
        """
        ...

