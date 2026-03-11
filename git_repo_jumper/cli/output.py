from rich.console import Console
from rich.panel import Panel


console = Console()


def print_error(message: str) -> None:
    """Prints an error message in a red panel using Rich."""
    print_panel(f'✗ {message}', 'red')


def print_warning(message: str) -> None:
    """Prints a warning message in a yellow panel using Rich."""
    print_panel(f'⚠ {message}', 'yellow')


def print_success(message: str) -> None:
    """Prints a success message in a green panel using Rich."""
    print_panel(f'✓ {message}', 'green')


def print_info(message: str) -> None:
    """Prints an info message in a cyan panel using Rich."""
    print_panel(f'ℹ {message}', 'cyan')


def print_panel(message: str, color: str) -> None:
    """Prints a message in a red panel with the given color using Rich."""
    formatted_message = f'[{color} bold]{message}[/{color} bold]'
    print_custom_panel(formatted_message, color)


def print_custom_panel(formatted_message: str, panel_color: str) -> None:
    """
    Prints a custom formatted message in a panel with the given color
    using Rich.
    """
    console.print(Panel(
        formatted_message,
        border_style=panel_color,
        padding=(1, 2)
    ))


def str_with_fixed_width(text: str, width: int, align: str = 'left') -> str:
    """
    Returns a string truncated or padded to fit the specified width.
    Alignment can be 'start', 'end', or 'center'.

    If the text is longer than the width, it will be truncated and ended with
    an ellipsis (…). If the text is shorter, it will be padded with spaces
    according to the specified alignment.

    Parameters:
    -----------
    text : str
        The input string to be formatted.
    width : int
        The desired width of the output string.
    align : str, optional
        The alignment of the text within the width: 'left', 'right' or 'center'
        (by default 'left').

    Examples:
    ---------
    >>> str_with_fixed_width('Hello, World!', 10)
    'Hello, Wo…'
    >>> str_with_fixed_width('Hello', 10)
    'Hello     '

    Raises:
    -------
    ValueError
        If the alignment is not one of 'left', 'right' or 'center'.

    Returns:
    --------
    str
        The formatted string with the specified width and alignment.
    """
    if len(text) > width:
        if align == 'right':
            return '…' + text[-(width - 1):]  # Truncate from left
        return text[:width - 1] + '…'         # Truncate from right

    if align == 'left':
        return text.ljust(width)
    elif align == 'right':
        return text.rjust(width)
    elif align == 'center':
        return text.center(width)
    else:
        raise ValueError(f'Invalid alignment: {align}')
