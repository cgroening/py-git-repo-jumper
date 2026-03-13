from pathlib import Path


class ConfigNotFoundError(Exception):
    """Raised when the configuration file is not found."""
    _config_path: Path


    def __init__(self, config_path: Path):
        self._config_path = config_path

    def __str__(self) -> str:
        return f'Configuration file not found:\n{str(self._config_path)}'


class ConfigParseError(Exception):
    """Raised when there is an error parsing the configuration file."""
    _config_path: Path
    _error_message: str


    def __init__(self, config_path: Path, error_message: str):
        self._config_path = config_path
        self._error_message = error_message

    def __str__(self) -> str:
        return f'Error parsing YAML file:\n{str(self._config_path)}\n\n' \
               + f'{self._error_message}'


class SelectedRepoPathSaveError(Exception):
    """Raised when there is an error saving the selected repo path on disk."""
    _selected_repo_path_file: str
    _error_message: str


    def __init__(self, _selected_repo_path_file: str, error_message: str):
        self._selected_repo_path_file = _selected_repo_path_file
        self._error_message = error_message

    def __str__(self) -> str:
        return ('Error saving selected repo path in:\n'
                f'{self._selected_repo_path_file}\n\n{self._error_message}')

class ConfiguredGitToolNotFoundError(Exception):
    """Raised when the configured git tool is not found in the system."""
    _git_tool_name: str
    _error_message: str | None = None


    def __init__(self, git_tool_name: str, e: str | None = None):
        self._git_tool_name = git_tool_name
        self._error_message = e

    def __str__(self) -> str:
        if (e := self._error_message):
            return f'Error opening {self._git_tool_name}:\n\n{str(e)}'
        else:
            return f'Configured git tool not found: {self._git_tool_name}'


class GitInfoCacheError(Exception):
    """Raised when there is an error saving or loading git info from storage."""
    _storage_path: Path
    _error_message: str | None = None


    def __init__(self, storage_path: Path, e: str | None = None):
        self._storage_path = storage_path
        self._error_message = e

    def __str__(self) -> str:
        if (e := self._error_message):
            return (
                'Error accessing git info cache at:\n'
                f'{str(self._storage_path)}\n\n'
                f'{str(e)}')
        else:
            return f'Error accessing git info cache at:\n{self._storage_path}'
