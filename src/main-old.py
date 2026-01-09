#!/usr/bin/env python3
"""
Git Repository Selector
Reads git repos from config.yaml and opens the selected repo in a git tool
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import questionary
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def load_config(config_path: str = "config.yaml") -> Tuple[List[Dict[str, str]], str]:
    """
    Loads the repository configuration from the YAML file.
    Returns a tuple of (repos list, git_program name).
    """
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        # Support both formats:
        # 1. Simple list of repos (old format)
        # 2. Dict with 'repos' and 'git_program' keys (new format)
        if isinstance(data, list):
            return data, "lazygit"
        elif isinstance(data, dict):
            repos = data.get("repos", [])
            git_program = data.get("git_program", "lazygit")
            return repos, git_program
        else:
            return [], "lazygit"

    except FileNotFoundError:
        console.print(f"[red]Error: {config_path} not found![/red]")
        sys.exit(1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML file: {e}[/red]")
        sys.exit(1)


def get_git_status(repo_path: str) -> Dict[str, any]:
    """Determines the git status of a repository."""
    path = Path(repo_path).expanduser()

    if not path.exists():
        return {
            "valid": False,
            "error": "Path does not exist",
            "branch": "",
            "status": "",
            "changes": 0
        }

    if not (path / ".git").exists():
        return {
            "valid": False,
            "error": "Not a git repository",
            "branch": "",
            "status": "",
            "changes": 0
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

        return {
            "valid": True,
            "error": None,
            "branch": branch,
            "status": status_text,
            "changes": changes
        }

    except subprocess.TimeoutExpired:
        return {
            "valid": False,
            "error": "Timeout",
            "branch": "",
            "status": "",
            "changes": 0
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "branch": "",
            "status": "",
            "changes": 0
        }


def create_repo_table(repos: List[Dict[str, str]]) -> Table:
    """Creates a Rich table with all repositories."""
    table = Table(title="📦 Git Repositories", show_header=True, header_style="bold magenta")

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Branch", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Path", style="dim")

    for repo in repos:
        git_info = get_git_status(repo["path"])

        if git_info["valid"]:
            status_style = "green" if git_info["changes"] == 0 else "yellow"
            table.add_row(
                repo["name"],
                git_info["branch"],
                Text(git_info["status"], style=status_style),
                repo["path"]
            )
        else:
            table.add_row(
                repo["name"],
                "[red]✗[/red]",
                f"[red]{git_info['error']}[/red]",
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
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    args = parser.parse_args()

    console.clear()

    # Load configuration
    repos, config_program = load_config(args.config)

    # CLI argument takes precedence over config file
    git_program = args.program if args.program else config_program

    # Header
    console.print(Panel.fit(
        f"[bold cyan]Git Repository Selector[/bold cyan]\n"
        f"[dim]Select a repository to open in {git_program}[/dim]",
        border_style="cyan"
    ))
    console.print()

    if not repos:
        console.print(f"[yellow]No repositories found in {args.config}![/yellow]")
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

    # Select repository
    choices = [
        {
            "name": format_repo_choice(r["repo"], r["git_info"]),
            "value": r["repo"]
        }
        for r in valid_repos
    ]

    selected = questionary.select(
        "Select repository:",
        choices=choices,
        style=questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),
            ('question', 'bold'),
            ('answer', 'fg:#2196f3 bold'),
            ('pointer', 'fg:#673ab7 bold'),
            ('highlighted', 'fg:#673ab7 bold'),
            ('selected', 'fg:#2196f3'),
        ])
    ).ask()

    if selected:
        console.print()
        console.print(f"[green]Opening {selected['name']} in {git_program}...[/green]")
        open_in_git_program(selected["path"], git_program)
    else:
        console.print("\n[yellow]Cancelled.[/yellow]")


if __name__ == "__main__":
    main()

