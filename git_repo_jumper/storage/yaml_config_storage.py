import yaml
from pathlib import Path
from git_repo_jumper.domain.models import Config, Repo
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.storage.config_storage import ConfigStorage


DEFAULT_CONFIG_PATH = Path.home() / '.config' / 'git-repo-jumper' / 'config.yaml'


class YamlConfigStorage(ConfigStorage):
    """
    Storage class for loading config from a YAML file.
    Implements the ConfigStorage interface.

    The YAML file should have the following structure:

    ```yaml
    git-program: lazygit
    github-username: your-github-username
    repos:
      - name: repo1           # Optional, defaults to folder name
        path: /path/to/repo1
        show: true            # Optional, defaults to true
        fav: true             # Optional, if true, repo will be marked as
                              # favorite and sorted first
      - ...
    ```

    Attributes:
    -----------
    _config_path: str
        The path to the YAML config file.
    """
    _config_path: Path


    def __init__(self, config_path: Path | None = None):
        """Sets the config path to default value if not provided."""
        if config_path is None:
            config_path = DEFAULT_CONFIG_PATH
        self._config_path = config_path

    def load_config(self) -> Config:
        """Loads the config from the YAML file and returns a Config object."""
        # Open YAML file
        try:
            with open(self._config_path, 'r') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ConfigNotFoundError(self._config_path)
        except yaml.YAMLError as e:
            raise ConfigParseError(self._config_path, str(e))

        # Parse config values
        git_program_name = self._parse_git_program(
            data.get('git-program', None)
        )
        github_username = self._parse_github_username(
            data.get('github-username', None)
        )
        repos = self._parse_repos(data.get('repos', None))

        return Config(
            config_path=self._config_path,
            git_tool_name=git_program_name,
            github_username=github_username,
            repos=repos
        )

    @staticmethod
    def _parse_git_program(git_program_name: str | None) -> str | None:
        return git_program_name

    @staticmethod
    def _parse_github_username(github_username: str | None) -> str | None:
        return github_username

    @staticmethod
    def _parse_repos(repos_raw: list | object | None) -> list[Repo] | None:
        """
        Parses the repos from the raw YAML data and returns a list of
        Repo objects.
        """
        # Skip if repos is not a list
        if not isinstance(repos_raw, list):
            return None

        # Loop through repos and create Repo objects
        repos: list[Repo] = []
        for repo in repos_raw:
            # Skip if no path is provided, as it's required
            if not (repo_path := repo.get('path', None)):
                continue

            # Use folder name as repo name if name is missing
            if not (repo_name := repo.get('name', None)):
                path = Path(repo_path).expanduser()
                repo_name = path.name

            repos.append(Repo(
                name=repo_name,
                path=repo_path,
                show=repo.get('show', True),
                fav=repo.get('fav', False)
            ))

        return repos
