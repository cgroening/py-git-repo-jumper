from git_repo_jumper.domain.models import Config, Repo
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

    def store_selected_repo_path(self, path: str) -> None:
        print(self._config.config_path)
        # selected_repo_path_file =
