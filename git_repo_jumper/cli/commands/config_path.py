from pathlib import Path
from git_repo_jumper.cli.output import (
    print_custom_panel, print_error
)
from git_repo_jumper.domain.models import Config
from git_repo_jumper.domain.errors import (
    ConfigNotFoundError, ConfigParseError
)
from git_repo_jumper.services.repository import GitRepoService


class ConfigPathCommand:
    """
    Command to display the current config file path.
    """
    _service: GitRepoService


    def __init__(self, service: GitRepoService):
        self._service = service

    def run(self) -> None:
        try:
            config: Config = self._service.get_config()
        except (ConfigNotFoundError, ConfigParseError) as e:
            print_error(str(e))
            return
        except Exception as e:
            print_error(f'Unexpected error while reading config: {str(e)}')
            return

        self._display_config_path(config.config_path)

    @staticmethod
    def _display_config_path(path: Path) -> None:
        print_custom_panel(
            formatted_message=(
                f'Current config file path:\n\n'
                f'[bold magenta]{str(path)}[/bold magenta]'
            ),
            panel_color='cyan'
        )
