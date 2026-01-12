
"""
Git Repository Selector

Reads git repos from config.yaml and opens the selected repo in a git tool.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
import yaml
from rich.console import Console
from rich.panel import Panel


console = Console()


def load_config(config_path: str | None = None) \
-> Tuple[List[Dict[str, str]], str, str, Path] | None:
    """
    Loads the repository configuration from the YAML file.

    Tries custom config path first, then falls back to script directory.

    Parameters:
    -----------
    config_path : str | None
        Path to custom config file. If None, uses default in script directory.

    Returns:
    --------
    Tuple[List[Dict[str, str]], str, str, Path] | None
        A tuple containing:
        - List of repository dictionaries with keys: name, path, show (optional)
        - GitHub username (str)
        - Git program name (str)
        - Path to the actual config file used (Path)
    """
    script_dir = Path(__file__).parent
    default_config = script_dir / "config.yaml"

    # Determine which config file to try
    configs_to_try: List[Tuple[str, Path]] = []

    if config_path is not None:
        # Custom config is given - try it first
        custom_path = Path(config_path)
        configs_to_try.append(("custom", custom_path))

    # Add script directory as fallback
    configs_to_try.append(("default", default_config))

    # Try each config in order
    for _, config_file in configs_to_try:
        try:
            # Load YAML file and get git program + repos
            with open(config_file, "r") as f:
                data = yaml.safe_load(f)
                repos = data.get("repos", [])
                github_username = data.get("github-username", "")
                git_program = data.get("git-program", "lazygit")

            # Use folder name as repo name if name is missing
            for repo in repos:
                if "name" not in repo or not repo["name"]:
                    path = Path(repo["path"]).expanduser()
                    repo["name"] = path.name

            # Filter out repos with show: false
            repos = [repo for repo in repos if repo.get("show", True)]

            return repos, github_username, git_program, config_file.absolute()

        except FileNotFoundError:
            console.print("[red]✗ Config file not found![/red]")
            break
        except yaml.YAMLError as e:
            # YAML parsing error - don't try fallback, this is a real error
            console.print()
            console.print(Panel(
                f"[red]✗ Error parsing YAML file[/red]\n\n"
                f"[yellow]File:[/yellow] [cyan]{config_file}[/cyan]\n\n"
                f"[dim]{str(e)}[/dim]",
                border_style="red",
                padding=(1, 2)
            ))
            sys.exit(1)

    # If this code is reached, no valid config was found
    return None


def get_github_repo_name(repo_path: str, github_username: str = "") -> str:
    """
    Extracts the GitHub repository name from git remote URL.

    Parameters:
    -----------
    repo_path : str
        Path to the remote repository.
    github_username : str
        GitHub username to remove from the repo name if present.

    Returns:
    --------
    str
        GitHub repository name in "owner/repo" format or "-" if not found.
    """
    path = Path(repo_path).expanduser()

    if not (path / ".git").exists():
        return "-"

    try:
        # Get remote URL
        remote_result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )

        if remote_result.returncode != 0:
            return "-"

        remote_url = remote_result.stdout.strip()

        # Parse GitHub URL (both HTTPS and SSH formats)
        # HTTPS: https://github.com/user/repo.git
        # SSH: git@github.com:user/repo.git

        if "github.com" not in remote_url:
            return "-"

        # Extract owner/repo
        if remote_url.startswith("git@github.com:"):
            # SSH format: git@github.com:user/repo.git
            repo_part = remote_url.replace("git@github.com:", "")
        elif "github.com/" in remote_url:
            # HTTPS format: https://github.com/user/repo.git
            repo_part = remote_url.split("github.com/")[1]
        else:
            return "-"

        # Remove .git suffix if present
        repo_part = repo_part.replace(".git", "")

        # Remove GitHub username "cgroening/" if present
        repo_part = repo_part.replace(f"{github_username}/", "")

        return repo_part

    except (subprocess.TimeoutExpired, Exception):
        return "-"

def get_git_status(repo_path: str, github_username: str = "") -> Dict[str, any]:
    """
    Determines the git status of a repository.

    Parameters:
    -----------
    repo_path : str
        Path to the repository.
    github_username : str
        GitHub username to use when extracting repo name.

    Returns:
    --------
    Dict[str, any]
        A dictionary with keys:
        - valid: bool
        - error: str | None
        - branch: str
        - status: str
        - changes: int
        - github_repo: str
    """
    # TODO: Replace the returned dict with a dataclass for better type safety

    # Get path object and check if it exists and is a git repo
    path = Path(repo_path).expanduser()

    if not path.exists():
        return {
            "valid": False,
            "error": "Path does not exist",
            "branch": "",
            "status": "",
            "changes": 0,
            "github_repo": "-"
        }

    if not (path / ".git").exists():
        return {
            "valid": False,
            "error": "Not a git repository",
            "branch": "",
            "status": "",
            "changes": 0,
            "github_repo": "-"
        }

    # Gather git information
    try:
        # Current branch
        branch_result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )

        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip()
        else:
            branch = "unknown"

        # Get changes
        status_result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )

        if status_result.stdout.strip():
            changes = len(status_result.stdout.strip().split('\n'))
        else:
            changes = 0

        # Check upstream status
        upstream_result = subprocess.run(
            ["git", "-C", str(path), "rev-list", "--count", "--left-right",
             "@{upstream}...HEAD"],
            capture_output=True, text=True, timeout=5
        )

        status_text = "✓ Clean"
        if changes > 0:
            status_text = f"≠ {changes} change{'s' if changes != 1 else ''}"

        if upstream_result.returncode == 0:
            behind, ahead = upstream_result.stdout.strip().split()
            if int(behind) > 0:
                status_text += f" ↓{behind}"
            if int(ahead) > 0:
                status_text += f" ↑{ahead}"

        # Get GitHub repo name
        github_repo = get_github_repo_name(repo_path, github_username)

        return {
            "valid": True,
            "error": None,
            "branch": branch,
            "status": status_text,
            "changes": changes,
            "github_repo": github_repo
        }

    except subprocess.TimeoutExpired:
        return {
            "valid": False,
            "error": "Timeout",
            "branch": "",
            "status": "",
            "changes": 0,
            "github_repo": "-"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "branch": "",
            "status": "",
            "changes": 0,
            "github_repo": "-"
        }


def format_repo_choice(repo: Dict[str, str], git_info: Dict[str, any]) -> str:
    """Formats a repository entry for questionary."""
    if git_info["valid"]:
        status_icon = "✓" if git_info["changes"] == 0 else "⚡"
        return f"{status_icon} {repo['name']} [{git_info['branch']}] - {git_info['status']}"
    else:
        return f"✗ {repo['name']} - {git_info['error']}"


def format_repo_table_line(repo: Dict[str, str], git_info: Dict[str, any],
                           max_name: int = 20, max_branch: int = 10,
                           max_status: int = 15, max_github: int = 20,
                           max_path: int = 30) -> str:
    """
    Formats a repository entry as a table row for fuzzy finder.
    Returns plain text (InquirerPy doesn't support Rich markup).
    """
    if not git_info["valid"]:
        # Invalid repo - show error
        name = repo["name"][:max_name].ljust(max_name)
        error = git_info["error"][:max_status].ljust(max_status)
        path = repo["path"][:max_path].ljust(max_path)
        return f"✗ {name} │ {'':10} │ {error} │ {'':20} │ {path}"

    # Format each column with truncation and padding
    name = repo["name"][:max_name].ljust(max_name)
    branch = git_info["branch"][:max_branch].ljust(max_branch)
    status = git_info["status"][:max_status].ljust(max_status)
    github = git_info["github_repo"][:max_github].ljust(max_github)

    # Truncate path intelligently (show end if too long)
    path = repo["path"]
    if len(path) > max_path-2:
        # Show beginning and end
        path = "..." + path[-(max_path-5):]
    path = path.ljust(max_path)

    # Status icon (no color markup for InquirerPy)
    icon = "✓" if git_info["changes"] == 0 else "≠"

    return f"{icon} {name} │ {branch} │ {status} │ {github} │ {path}"


def create_table_header(max_name: int = 20, max_branch: int = 10,
                       max_status: int = 15, max_github: int = 20,
                       max_path: int = 30) -> None:
    """Creates a styled table header for the fuzzy finder using Rich."""
    from rich.table import Table

    # Create a Rich table for the header
    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))

    table.add_column("", style="dim", width=1)  # Icon column
    table.add_column(" Name", style="bold cyan", width=max_name, no_wrap=True)
    table.add_column(" Branch", style="bold green", width=max_branch, no_wrap=True)
    table.add_column("Status", style="bold yellow", width=max_status, no_wrap=True)
    table.add_column(" GitHub Repo Name", style="bold blue", width=max_github, no_wrap=True)
    table.add_column("  Path", style="bold dim", width=max_path, no_wrap=True)

    console.print(table)


def open_in_git_program(repo_path: str, git_program: str = "lazygit") -> None:
    """Opens the repository in the specified git program."""
    path = Path(repo_path).expanduser()

    # Program-specific commands
    commands = {
        "lazygit": ["lazygit", "-p", str(path)],
        "gitui": ["gitui", "-d", str(path)],
        "tig": ["tig", "-C", str(path)],
        "gh": ["gh", "repo", "view", "--web"],  # Opens in browser
    }

    # Use custom command if provided, otherwise use known commands
    if git_program in commands:
        cmd = commands[git_program]
    else:
        # For unknown programs, assume they accept -p or -C flag
        cmd = [git_program, "-p", str(path)]

    try:
        # Special handling for gh (needs to run from within the repo)
        if git_program == "gh":
            subprocess.run(cmd, cwd=str(path), check=True)
        else:
            subprocess.run(cmd, check=True)
    except FileNotFoundError:
        console.print(f"[red]Error: {git_program} is not installed![/red]")
        console.print(f"Install it or specify a different program with --program flag")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error opening {git_program}: {e}[/red]")
        sys.exit(1)


def cleanup_old_last_repo(config_dir: Path, keep_last_repo: bool = True):
    """
    Optionally cleans up old last-repo.txt file.

    Args:
        config_dir: Directory where config file is located
        keep_last_repo: If False, deletes existing last-repo.txt
    """
    last_repo_file = config_dir / "last-repo.txt"

    if not keep_last_repo and last_repo_file.exists():
        try:
            last_repo_file.unlink()
        except Exception as e:
            # Silently ignore errors - this is just cleanup
            pass


def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Select and open a git repository in your preferred git tool"
    )
    parser.add_argument(
        "-p", "--program",
        type=str,
        help="Git program to use (lazygit, gitui, tig, etc.)",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to config file (default: config.yaml in script directory)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove last-repo.txt before starting (clean slate)",
    )
    args = parser.parse_args()

    console.clear()

    # Load configuration (will use script directory if no config specified)
    repos, github_username, config_program, config_file_path = load_config(args.config)

    # CLI argument takes precedence over config file
    git_program = args.program if args.program else config_program

    # Determine directory for last-repo.txt (same as config file)
    config_dir = config_file_path.parent
    last_repo_file = config_dir / "last-repo.txt"

    # Optional cleanup of old last-repo.txt
    if args.clean:
        cleanup_old_last_repo(config_dir, keep_last_repo=False)

    # Header with Rich styling
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]📦 Git Repository Selector[/bold cyan]\n"
        f"[dim]Select a repository to open in [bold]{git_program}[/bold][/dim]\n"
        f"[dim italic]Type to filter • ↑/↓ to navigate • Enter to select[/dim italic]",
        border_style="cyan",
        padding=(1, 2)
    ))
    console.print()

    if not repos:
        # Show which config file was used
        config_used = args.config if args.config else str(config_file_path)
        console.print()
        console.print(Panel(
            f"[yellow]⚠ No repositories found in config[/yellow]\n"
            f"[dim]Config file: {config_used}[/dim]",
            border_style="yellow",
            padding=(1, 2)
        ))
        sys.exit(0)

    # Get git status for all repos
    repos_with_status = []
    for repo in repos:
        git_info = get_git_status(repo["path"], github_username)
        repos_with_status.append({
            "repo": repo,
            "git_info": git_info
        })

    # Sort by repository name (case-insensitive)
    repos_with_status.sort(key=lambda r: r["repo"]["name"].lower())

    # Separate valid and invalid repos
    valid_repos = [r for r in repos_with_status if r["git_info"]["valid"]]
    invalid_repos = [r for r in repos_with_status if not r["git_info"]["valid"]]


    # Show invalid repos in red panel if any exist
    if invalid_repos:
        console.print()
        console.print(Panel(
            "[bold red]⚠ Repositories not found or invalid:[/bold red]\n\n" +
            "\n".join([
                f"  [red]✗[/red] [yellow]{repo['repo']['name']}[/yellow] - [dim]{repo['git_info']['error']}[/dim]\n"
                f"    [dim]Path: {repo['repo']['path']}[/dim]"
                for repo in invalid_repos
            ]),
            border_style="red",
            padding=(1, 2),
            title="[red]Errors[/red]",
            title_align="left"
        ))
        console.print()


    # Only valid repos for selection
    valid_repos = [r for r in repos_with_status if r["git_info"]["valid"]]

    if not valid_repos:
        console.print()
        console.print(Panel(
            "[red]✗ No valid git repositories found![/red]\n"
            "[dim]Check that paths in config.yaml point to valid git repositories[/dim]",
            border_style="red",
            padding=(1, 2)
        ))
        sys.exit(1)

    # Calculate max widths for table columns
    max_name = max(len(r["repo"]["name"]) for r in valid_repos) if valid_repos else 20
    max_name = min(max(max_name, 15), 30)  # Between 15 and 30 chars

    max_branch = max(len(r["git_info"]["branch"]) for r in valid_repos) if valid_repos else 10
    max_branch = min(max(max_branch, 8), 15)

    max_github = max(len(r["git_info"]["github_repo"]) for r in valid_repos) if valid_repos else 20
    max_github = min(max(max_github, 15), 25)

    # Display table header with Rich styling
    create_table_header(max_name+1, max_branch+2, 15, max_github, 35)
    console.print()

    # Select repository with fuzzy finder (table-like format with Rich colors)
    choices = []
    repo_map = {}

    for r in valid_repos:
        repo = r["repo"]
        git_info = r["git_info"]
        choice_text = format_repo_table_line(repo, git_info, max_name, max_branch, 15, max_github, 35)
        choices.append(Choice(value=repo, name=choice_text))
        repo_map[choice_text] = repo

    selected = inquirer.fuzzy(
        message="Select repository (type to filter):",
        choices=choices,
        default="",
        max_height="70%",
        border=True,
        info=True,
        match_exact=False,
        marker="❯",
        marker_pl=" ",
    ).execute()

    if not selected:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return

    if selected:
        console.print()
        console.print(Panel(
            f"[bold green]✓[/bold green] Opening [bold cyan]{selected['name']}[/bold cyan] in [bold magenta]{git_program}[/bold magenta]",
            border_style="green",
            padding=(0, 2)
        ))
        open_in_git_program(selected["path"], git_program)

        # Save path in last-repo.txt in same directory as config
        try:
            with open(last_repo_file, "w") as f:
                f.write(selected["path"])
        except Exception as e:
            console.print(f"[red]Error saving last-repo.txt: {e}[/red]")
    else:
        console.print()
        console.print(Panel(
            "[yellow]✗ Cancelled[/yellow]",
            border_style="yellow",
            padding=(0, 2)
        ))


if __name__ == "__main__":
    main()
