from pathlib import Path
from git_repo_jumper.domain.models import Config
from git_repo_jumper.storage.config_storage import ConfigStorage


class GitRepoService:
    _storage: ConfigStorage


    def __init__(self, storage: ConfigStorage):
        self._storage = storage

    def list_repos(self, config_path: Path | None = None) -> Config:
        self._storage.set_config_path(config_path)
        return self._storage.load_config()
