from git_repo_jumper.domain.models import Repo
from git_repo_jumper.storage.config_storage import ConfigStorage


class GitRepoService:
    _storage: ConfigStorage


    def __init__(self, storage: ConfigStorage):
        self._storage = storage

    def fetch_repos(self) -> list[Repo] | None:
        config = self._storage.load_config()
        return config.repos
