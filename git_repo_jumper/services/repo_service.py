from pathlib import Path
from git_repo_jumper.domain.models import Config
from git_repo_jumper.storage.config_storage import ConfigStorage


class GitRepoService:
    _storage: ConfigStorage
    _config: Config


    def __init__(self, storage: ConfigStorage):
        self._storage = storage

    def fetch_repos(self, config_path: Path | None = None) -> list | None:
        self._storage.set_config_path(config_path)
        self._config = self._storage.load_config()
        return self._config.repos
