class ConfigNotFoundError(Exception):
    """Raised when the configuration file is not found."""
    _config_path: str


    def __init__(self, config_path: str):
        self._config_path = config_path

    def __str__(self) -> str:
        return f'Configuration file not found:\n{self._config_path}'


class ConfigParseError(Exception):
    """Raised when there is an error parsing the configuration file."""
    _config_path: str
    _error_message: str


    def __init__(self, config_path: str, error_message: str):
        self._config_path = config_path
        self._error_message = error_message

    def __str__(self) -> str:
        return f'Error parsing YAML file:\n{self._config_path}\n\n' \
               + f'{self._error_message}'
