from git_repo_jumper.domain.models import Config, Repo
from git_repo_jumper.storage.config_storage import ConfigStorage


class GitRepoService:
    _storage: ConfigStorage
    _config: Config


    def __init__(self, storage: ConfigStorage):
        self._storage = storage
        self._config = self._storage.load_config()

    def fetch_repos(self) -> list[Repo] | None:
        return self._config.repos

    def get_git_tool_name(self) -> str | None:
        return self._config.git_tool_name

    def store_selected_repo_path(self, path: str) -> None:
        print(self._config.config_path)
        # selected_repo_path_file =
