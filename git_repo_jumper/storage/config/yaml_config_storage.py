import yaml
from pathlib import Path
from git_repo_jumper.domain.models import (
    Config, Repo, RepoSelectorColumnWidths, GitInfo
)
from git_repo_jumper.domain.errors import ConfigNotFoundError, ConfigParseError
from git_repo_jumper.storage.config.config_storage import BaseConfigStorage


DEFAULT_CONFIG_PATH = Path.home() / '.config' / 'git-repo-jumper' / 'config.yaml'


class YamlConfigStorage(BaseConfigStorage):
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

    Attributes
    ----------
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
        """
        Loads the config from the YAML file and returns a Config object.

        Raises
        ------
        ConfigNotFoundError
            If the config file is not found at the specified path.
        ConfigParseError
            If there is an error parsing the YAML file.

        Returns
        -------
        Config: The loaded configuration data.
        """
        # Open YAML file
        try:
            with open(self._config_path, 'r') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ConfigNotFoundError(self._config_path)
        except yaml.YAMLError as e:
            raise ConfigParseError(self._config_path, str(e))

        # Parse config values
        repo_selector_column_widths = self._parse_repo_selector_column_widths(
            data.get('repo-selector-column-widths', None)
        )

        git_tool_name = self._parse_git_program(
            data.get('git-program', None)
        )
        github_username = self._parse_github_username(
            data.get('github-username', None)
        )
        repos = self._parse_repos(data.get('repos', None))

        example_mode = data.get('example-mode', False)

        return Config(
            config_path=self._config_path,
            repo_selector_column_widths=repo_selector_column_widths,
            git_tool_name=git_tool_name,
            github_username=github_username,
            repos=repos,
            example_mode=example_mode,
        )

    @staticmethod
    def _parse_repo_selector_column_widths(column_widths_raw: dict | None) \
    -> RepoSelectorColumnWidths:
        """
        Parses the repo selector column widths from the raw YAML data and
        returns a RepoSelectorColumnWidths object.
        """
        if not isinstance(column_widths_raw, dict):
            return RepoSelectorColumnWidths()

        default_widths = RepoSelectorColumnWidths()

        return RepoSelectorColumnWidths(
            name=column_widths_raw.get('name', default_widths.name),
            current_branch_name=column_widths_raw.get(
                'current_branch_name', default_widths.current_branch_name
            ),
            status=column_widths_raw.get('status', default_widths.status),
            github_repo_name=column_widths_raw.get(
                'github_repo_name', default_widths.github_repo_name
            )
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
                fav=repo.get('fav', False),
                example_git_info=YamlConfigStorage._parse_example_git_info(
                    repo.get('example-git-info', None)
                )
            ))

        return repos

    @staticmethod
    def _parse_example_git_info(example_git_info_raw: dict | None) -> GitInfo:
        """
        Parses the example git info from the raw YAML data and returns a
        GitInfo object.
        """
        if not isinstance(example_git_info_raw, dict):
            return GitInfo.invalid('Invalid example_git_info format')

        return GitInfo(
            current_branch_name=example_git_info_raw.get(
                'current-branch-name', 'main'
            ),
            status=example_git_info_raw.get('status', '✓'),
            github_repo_name=example_git_info_raw.get('github-repo-name', None),
            valid=True
        )

