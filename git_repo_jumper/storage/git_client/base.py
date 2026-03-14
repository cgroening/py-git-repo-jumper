from abc import ABC, abstractmethod
from git_repo_jumper.domain.models import GitInfo


class BaseGitClient(ABC):
    @abstractmethod
    def get_git_status(
        self, repo_path: str, github_username: str | None, do_fetch: bool = False
    ) -> GitInfo:
        """Determines the git status of a repository."""
        ...

    @abstractmethod
    def open_git_tool(self, repo_path: str, git_program: str) -> None:
        """Opens the repository in the specified git program."""
        ...
