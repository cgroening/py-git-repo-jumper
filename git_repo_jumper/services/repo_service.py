from git_repo_jumper.domain.errors import SelectedRepoPathSaveError
from git_repo_jumper.domain.models import Config
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

    def store_selected_repo_path(self, repo_path: str) -> None:
        """
        Stores the path of the selected repository in a file named
        `selected-repo.txt` in the same directory as the config file.
        This allows external tools (e.g. a shell function) to read the path of
        the last opened repository after the git program exits and change the
        current directory of the terminal to that path.
        """
        config_parent_path = self.get_config().config_path.parent
        selected_repo_path_file = config_parent_path / 'selected-repo.txt.'

        try:
            with open(selected_repo_path_file, 'w') as f:
                f.write(repo_path)
        except Exception as e:
            raise SelectedRepoPathSaveError(str(selected_repo_path_file), str(e))
