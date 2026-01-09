
"""
Git Repository Selector

Reads git repos from config.yaml and opens the selected repo in a git tool.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def load_config(config_path: str = None) -> Tuple[List[Dict[str, str]], str, Path]:
    """
    Loads the repository configuration from the YAML file.
    Tries custom config path first, then falls back to script directory.
    Returns a tuple of (repos list, git_program name, config_file_path).
    """
    script_dir = Path(__file__).parent
    default_config = script_dir / "config.yaml"

    # Determine which config file to try
    configs_to_try = []

    if config_path is not None:
        # Custom config was specified - try it first
        custom_path = Path(config_path)
        configs_to_try.append(("custom", custom_path))
        # Add script directory as fallback
        configs_to_try.append(("default", default_config))
    else:
        # No custom config - only try script directory
        configs_to_try.append(("default", default_config))

    # Try each config in order
    last_error = None
    for config_type, config_file in configs_to_try:
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)

            # Successfully loaded - process the data
            if isinstance(data, list):
                repos = data
                git_program = "lazygit"
            elif isinstance(data, dict):
                repos = data.get("repos", [])
                git_program = data.get("git-program", "lazygit")
            else:
                repos = []
                git_program = "lazygit"

            # Auto-generate names from folder if not provided
            for repo in repos:
                if "name" not in repo or not repo["name"]:
                    path = Path(repo["path"]).expanduser()
                    repo["name"] = path.name

            # Show which config was used if custom was specified
            if config_path is not None and config_type == "default":
                console.print(f"[yellow]Custom config not found, using: {config_file}[/yellow]")

            # Return the actual config file path that was used
            return repos, git_program, config_file.absolute()

        except FileNotFoundError as e:
            last_error = e
            if config_type == "custom":
                # Custom config not found, will try fallback
                continue
            else:
                # Default config also not found - this is an error
                break
        except yaml.YAMLError as e:
            # YAML parsing error - don't try fallback, this is a real error
            console.print(f"[red]Error parsing YAML file {config_file}: {e}[/red]")
            sys.exit(1)

    # If we get here, no config was found
    if config_path is not None:
        console.print(f"[red]Error: Config file not found![/red]")
        console.print(f"[yellow]Tried:[/yellow]")
        console.print(f"  1. Custom: {Path(config_path).absolute()}")
        console.print(f"  2. Default: {default_config.absolute()}")
    else:
        console.print(f"[red]Error: {default_config} not found![/red]")

    console.print(f"[yellow]Tip: Place config.yaml in {script_dir}[/yellow]")
    sys.exit(1)


def get_github_repo_name(repo_path: str) -> str:
    """
    Extracts GitHub repository name from git remote URL.
    Returns "owner/repo" format or "-" if not a GitHub repo.
    """
    path = Path(repo_path).expanduser()

    if not (path / ".git").exists():
        return "-"

    try:
        # Get remote URL
        remote_result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5
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

        return repo_part

    except (subprocess.TimeoutExpired, Exception):
        return "-"


def get_git_status(repo_path: str) -> Dict[str, any]:
    """Determines the git status of a repository."""
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

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Get changes
        status_result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )

        changes = len(status_result.stdout.strip().split('\n')) if status_result.stdout.strip() else 0

        # Check upstream status
        upstream_result = subprocess.run(
            ["git", "-C", str(path), "rev-list", "--count", "--left-right", "@{upstream}...HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )

        status_text = "✓ Clean"
        if changes > 0:
            status_text = f"⚡ {changes} change{'s' if changes != 1 else ''}"

        if upstream_result.returncode == 0:
            behind, ahead = upstream_result.stdout.strip().split()
            if int(behind) > 0:
                status_text += f" ↓{behind}"
            if int(ahead) > 0:
                status_text += f" ↑{ahead}"

        # Get GitHub repo name
        github_repo = get_github_repo_name(repo_path)

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


def create_repo_table(repos: List[Dict[str, str]]) -> Table:
    """Creates a Rich table with all repositories."""
    table = Table(title="📦 Git Repositories", show_header=True, header_style="bold magenta")

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Branch", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("GitHub", style="blue", no_wrap=True)
    table.add_column("Path", style="dim")

    for repo in repos:
        git_info = get_git_status(repo["path"])

        if git_info["valid"]:
            status_style = "green" if git_info["changes"] == 0 else "yellow"
            github_style = "blue" if git_info["github_repo"] != "-" else "dim"
            table.add_row(
                repo["name"],
                git_info["branch"],
                Text(git_info["status"], style=status_style),
                Text(git_info["github_repo"], style=github_style),
                repo["path"]
            )
        else:
            table.add_row(
                repo["name"],
                "[red]✗[/red]",
                f"[red]{git_info['error']}[/red]",
                "-",
                repo["path"]
            )

    return table


def format_repo_choice(repo: Dict[str, str], git_info: Dict[str, any]) -> str:
    """Formats a repository entry for questionary."""
    if git_info["valid"]:
        status_icon = "✓" if git_info["changes"] == 0 else "⚡"
        return f"{status_icon} {repo['name']} [{git_info['branch']}] - {git_info['status']}"
    else:
        return f"✗ {repo['name']} - {git_info['error']}"


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
    repos, config_program, config_file_path = load_config(args.config)

    # CLI argument takes precedence over config file
    git_program = args.program if args.program else config_program

    # Determine directory for last-repo.txt (same as config file)
    config_dir = config_file_path.parent
    last_repo_file = config_dir / "last-repo.txt"

    # Optional cleanup of old last-repo.txt
    if args.clean:
        cleanup_old_last_repo(config_dir, keep_last_repo=False)

    # Header
    console.print(Panel.fit(
        f"[bold cyan]Git Repository Selector[/bold cyan]\n"
        f"[dim]Select a repository to open in {git_program}[/dim]",
        border_style="cyan"
    ))
    console.print()

    if not repos:
        # Show which config file was used
        config_used = args.config if args.config else str(config_file_path)
        console.print(f"[yellow]No repositories found in {config_used}![/yellow]")
        sys.exit(0)

    # Get git status for all repos
    repos_with_status = []
    for repo in repos:
        git_info = get_git_status(repo["path"])
        repos_with_status.append({
            "repo": repo,
            "git_info": git_info
        })

    # Display table
    table = create_repo_table(repos)
    console.print(table)
    console.print()

    # Only valid repos for selection
    valid_repos = [r for r in repos_with_status if r["git_info"]["valid"]]

    if not valid_repos:
        console.print("[red]No valid git repositories found![/red]")
        sys.exit(1)

    # Select repository with fuzzy finder
    choices = []
    repo_map = {}

    for idx, r in enumerate(valid_repos):
        repo = r["repo"]
        git_info = r["git_info"]
        choice_text = format_repo_choice(repo, git_info)
        choices.append(Choice(value=repo, name=choice_text))
        repo_map[choice_text] = repo

    selected = inquirer.fuzzy(
        message="Select repository (type to filter):",
        choices=choices,
        default="",
        max_height="70%",
        border=True,
        info=True,
    ).execute()

    if not selected:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return

    if selected:
        console.print()
        console.print(f"[green]Opening {selected['name']} in {git_program}...[/green]")
        open_in_git_program(selected["path"], git_program)

        # Save path in last-repo.txt in same directory as config
        try:
            with open(last_repo_file, "w") as f:
                f.write(selected["path"])
        except Exception as e:
            console.print(f"[red]Error saving last-repo.txt: {e}[/red]")
    else:
        console.print("\n[yellow]Cancelled.[/yellow]")


if __name__ == "__main__":
    main()
