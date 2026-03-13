import json
from pathlib import Path
from git_repo_jumper.domain.models import GitInfo
from git_repo_jumper.domain.errors import GitInfoCacheError
from git_repo_jumper.storage.git_info_storage import GitInfoStorage


CACHE_FILE_NAME = 'git-info-cache.json'


class JsonGitInfoStorage(GitInfoStorage):
    _storage_path: Path


    def __init__(self, storage_parent_path: Path | None = None) -> None:
        self.set_storage_parent_path(storage_parent_path)

    def set_storage_parent_path(
            self, storage_parent_path: Path | str | None
    ) -> None:
        """Set the path to the configuration file if provided is not None."""
        if not storage_parent_path:
            return

        try:
            self._storage_path = Path(storage_parent_path) / CACHE_FILE_NAME
            if not self._storage_path.exists():
                self._storage_path.write_text(json.dumps({}))
        except Exception as e:
            raise GitInfoCacheError(self._storage_path, str(e))

    def save_git_info(
        self,
        git_infos: dict[str, GitInfo],
        date_and_time_iso: str
    ) -> None:
        """
        Stores the given Git infos in the JSON file (cache file) with the
        following structure:
        {
            "date_and_time": "2026-03-13T15:18:44.175330+01:00",
            "repos": [
                {
                    "path": "/path/to/repo1",
                    "git_info": {
                        "valid": true,
                        "error": null,
                        "current_branch": "main",
                        "status": "\u2713",
                        "changes": 0,
                        "github_repo_name": "remote-repo-name"
                    }
                },
                ...
        """
        dict_for_json_file = {
            'date_and_time': date_and_time_iso,
            'repos': []
        }

        for path, git_info in git_infos.items():
            path: str
            git_info: GitInfo
            dict_for_json_file['repos'].append({
                'path': path,
                'git_info': {
                    'valid': git_info.valid,
                    'error': git_info.error,
                    'current_branch': git_info.current_branch_name,
                    'status': git_info.status,
                    'changes': git_info.changes,
                    'github_repo_name': git_info.github_repo_name,
                }
            })

        with self._storage_path.open('w') as f:
            json.dump(dict_for_json_file, f, indent=4)

    def get_git_info(self) -> tuple[str | None, dict[str, GitInfo]] | None:
        """
        Returns all cached Git infos from the JSON file.

        Returns:
        --------
        tuple[str | None, dict[str, GitInfo]] | None:
            A tuple containing the date and time string of when the Git infos
            were cached and a dictionary mapping repository paths to their
            corresponding GitInfo objects. Returns None if the cache file does
            not exist.
        """
        if not self._storage_path.exists():
            return None

        with self._storage_path.open('r') as f:
            data = json.load(f)

        date_and_time_str = data.get('date_and_time', None)
        repos = data.get('repos', [])

        git_infos = {}
        for repo in repos:
            path = repo['path']
            git_info_data = repo['git_info']
            git_info = GitInfo(
                valid=git_info_data['valid'],
                error=git_info_data['error'],
                current_branch_name=git_info_data['current_branch'],
                status=git_info_data['status'],
                changes=git_info_data['changes'],
                github_repo_name=git_info_data['github_repo_name'],
            )
            git_infos[path] = git_info

        return date_and_time_str, git_infos

