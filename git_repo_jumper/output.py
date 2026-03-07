from rich.console import Console
from rich.panel import Panel


console = Console()


def print_error(message: str) -> None:
    """Prints an error message in a red panel using Rich."""
    console.print(Panel(
        f'[red bold]✗ {message}[/red bold]',
        border_style='red',
        padding=(1, 2)
    ))
