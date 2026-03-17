# 🐙 🚀 Git Repo Jumper

A fast and elegant terminal-based Git repository selector with fuzzy finding. Quickly navigate between your repositories and open them in your favorite Git TUI tool.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
[![PyPI](https://img.shields.io/pypi/v/git-repo-jumper)](https://pypi.org/project/git-repo-jumper/)

<img src="https://raw.githubusercontent.com/cgroening/py-git-repo-jumper/main/images/logo_dark_1.png" width="200" alt="Git Repo Jumper Logo">

![Screenshot](https://raw.githubusercontent.com/cgroening/py-git-repo-jumper/main/images/screenshot.png)

## ✨ Features

- 🔍 **Fuzzy Finder** – Type to filter repositories instantly across all fields
- 📊 **Table Display** – Clean table-like interface showing name, branch, status, GitHub repo and path
- 🎨 **Beautiful UI** – Rich-styled panels and headers with color-coded information
- ⚡ **Git Status** – Real-time status showing clean repos, changes and upstream differences (↓↑)
- ⏳ **Progress Bar** – Animated progress bar while loading git status of the repositories
- 🐙 **GitHub Integration** – Automatically extracts and displays GitHub repository names
- 🚨 **Error Handling** – Invalid repositories shown in a red panel before selection
- 📂 **Auto-naming** – Uses folder names if no explicit name is provided
- 🔧 **Flexible** – Works with lazygit, gitui, tig or any other Git TUI tool
- 📝 **Shell Integration** – Supports directory changing via `selected-repo.txt`
- 🏷️ **Filtering** – Hide repositories with `show: false`

### Planned features

- [x] Favorite/Bookmarked Repositories
- [ ] Recent Repositories History

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- Git
- A Git TUI tool (recommended):
-
  ```zsh
  # macOS
  brew install lazygit

  # Linux (Debian/Ubuntu)
  apt install lazygit
  ```

### Install

### Via pip

```zsh
pip install git-repo-jumper
```

[git-repo-jumper on PyPI](https://pypi.org/project/git-repo-jumper/)

### From Source

1. Clone this repository:
   ```zsh
   git clone https://github.com/cgroening/py-git-repo-jumper.git
   cd py-git-repo-jumper
   ```

2. Install the package if you want the `rjump` command available globally:

```zsh
uv pip install .
```

Alternatively, Git Repo Jumper can be run without installation, see Section [Without Installation](#without-installation).

3. Create your `config.yaml`: See [Configuration](#-configuration)

4. (Optional) Set up shell integration (see [Shell Integration](#-shell-integration))

## ⚙️ Configuration

Create a `config.yaml` file in `~/.config/git-repo-jumper/`. Alternatively, you can place the configuration file at a location of a choice and pass the path with the `--config` option.

```yaml
# Git program to use (lazygit, gitui, tig, gh, etc.)
git-program: lazygit

# Your GitHub username (optional - shortens remote repo names)
github-username: yourusername

# Column widths for the repository selector (fuzzy finder).
# The available width is first distributed to meet these minimum values.
# If the content of a column exceeds its configured width, the column
# is automatically expanded to fit if extra space is available.
repo-selector-column-widths:
  name: 30
  current_branch_name: 14
  status: 6
  github_repo_name: 20

# List of repositories
repos:
  # With explicit name
  - name: My Project
    path: ~/projects/my-project
    fav: true

  # Without name - uses folder name "dotfiles"
  - path: ~/dotfiles

  # Hide from list
  - name: Old Project
    path: ~/old-project
    show: false

  # iCloud/Obsidian vault example
  - name: Notes
    path: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/MyVault
```

### Configuration Options

| Option | Type | Required | Description | Default |
|--------|------|----------|-------------|---------|
| `git-program` | string | No | Git TUI tool to use | – |
| `github-username` | string | No | Your GitHub username (removes from display) | `""` |
| `repo-selector-column-widths` | map | No | Column widths for the repository selector (fuzzy finder) | `{}` |
| `repos` | list | Yes | List of repository configurations | `[]` |
| `repos[].name` | string | No | Display name | folder name |
| `repos[].path` | string | Yes | Full path to repository | - |
| `repos[].show` | boolean | No | Whether to show in list | `true` |
| `repos[].fav` | boolean | No | Whether to stick to top | `false` |

## 📖 Usage

### Basic Usage

```zsh
# Run directly
rjump         # defaults to rjump select
rjump select

# Or with shell function (if configured)
rj
```

### Without Installation

The package can also be run without installation from the project root:

```zsh
python -m git_repo_jumper
```

### Command Line Commands and Options

```zsh
# Use a custom config file
rjump -C ~/my-repos.yaml
rjump --config ~/my-repos.yaml

# Save path of selected repo to selected-repo.txt only
# and do not open git tool like lazygit
rjump select -s
rjump select --save-only

# Fetch latest changes of remote repos
rjump select -f
rjump select --fetch

# Open with cached git info instead of fetching fresh info
rjump select -c
rjump select --cached

# Show the path of the configuration file
jump config-path
```

## 🐚 Shell Integration

Add a shell function to your `~/.zshrc` or `~/.bashrc` for easy access.

If you want to cd in to the selected repository after exiting the git program, add this to your shell function (**make sure to change `last_repo_file`**):

```zsh
# ============================================================================ #
# rj - Git Repo Jumper shortcut
#
# Runs the Git Repo Jumper script and changes to the selected repository
# after the script is closed (= Lazygit was closed).
# ============================================================================ #
rj() {
    # Run the Git Repo Jumper script
    rjump "$@"

    # Change to cwd to the last selected repo
    local last_repo_file="/Users/<USERNAME>/Dotfiles/git-repo-jumper/selected-repo.txt"
    if [[ -f "$last_repo_file" ]]; then
        local target_dir=$(cat "$last_repo_file")
        if [[ -d "$target_dir" ]]; then
            cd "$target_dir" || return
            echo "Changed to: $(pwd)"
        else
            echo "Directory does not exist: $target_dir"
        fi
    else
        echo "Last repo file not found."
    fi
}

r() { rj "$@" }
rs() { rj select -s "$@" }
rf() { rj select -f "$@" }
rr() { rj select -c "$@" }
```

Then reload your shell:
```zsh
source ~/.zshrc  # or ~/.bashrc
```

Now simply run:
```zsh
rj
```

## 🎯 Features in Detail

### Fuzzy Finder

Type to filter repositories in real-time. Matches across:
- Repository names
- Branch names
- Git status
- GitHub repository names
- File paths

**Example:** Type "api" to instantly filter all repositories containing "api" in any field.

### Git Status Indicators

| Icon | Meaning |
|------|---------|
| ✓ | Clean repository (no uncommitted changes) |
| ≠ | Repository has uncommitted changes |
| ✗ | Invalid repository (not found or not a git repo) |
| ↓N | N commits behind upstream |
| ↑N | N commits ahead of upstream |

### Error Display

Invalid repositories are shown in a red error panel **before** the selection interface:

- **Path does not exist** - Repository location not found
- **Not a git repository** - Valid path but no .git directory
- **Timeout** - Git commands took too long

This allows you to quickly identify and fix configuration issues.

### GitHub Integration

The `github-username` config option shortens repository names for cleaner display:

**Without username config:**
```
yourusername/my-project  →  yourusername/my-project
yourusername/dotfiles    →  yourusername/dotfiles
```

**With username configured:**
```
yourusername/my-project  →  my-project
yourusername/dotfiles    →  Dotfiles
otherusername/repo       →  otherusername/repo  (unchanged)
```

### Alphabetical Sorting

All repositories are sorted alphabetically by name (case-insensitive) for easy scanning.

### Hidden Repositories

Use `show: false` to hide repositories from the list while keeping them in your config:

```yaml
repos:
  - name: Active Project
    path: ~/projects/active

  - name: Archived Project
    path: ~/projects/archived
    show: false  # Won't appear in the list
```

## 📋 Requirements

- Python 3.10+
- InquirerPy >= 0.3.4
- PyYAML >= 6.0.0
- rich >= 13.0.0

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [InquirerPy](https://github.com/kazhala/InquirerPy) – Beautiful interactive prompts
- [Rich](https://github.com/Textualize/rich) – Rich text and beautiful formatting in the terminal
- [lazygit](https://github.com/jesseduffield/lazygit) – Amazing Git TUI

## 💡 Tips

- Press `Ctrl+C` to cancel at any time
- The fuzzy finder searches across all visible columns
- Invalid repos are shown but not selectable
- Paths support `~` for home directory expansion

## 🐛 Troubleshooting

**Issue:** "Config file not found"
- **Solution:** Create `config.yaml` in `~/.config/git-repo-jumper/` or use `--config` flag

**Issue:** "No valid git repositories found"
- **Solution:** Check that paths in config.yaml are correct and point to git repositories

**Issue:** Git program not found
- **Solution:** Install the git tool (e.g., `brew install lazygit`) and set it in the `config.yaml`

**Issue:** Repository shows as invalid
- **Solution:** Verify the path exists and contains a `.git` directory