from pathlib import Path
from abc import ABC, abstractmethod
from git_repo_jumper.domain.models import Config


class BaseConfigStorage(ABC):
    """Interface for loading configuration data for git-repo-jumper."""

    _config_path: Path


    def set_config_path(self, config_path: Path | str | None) -> None:
        """Set the path to the configuration file if provided is not None."""
        if not config_path:
            return

        self._config_path = Path(config_path)

    @abstractmethod
    def load_config(self) -> Config:
        ...
