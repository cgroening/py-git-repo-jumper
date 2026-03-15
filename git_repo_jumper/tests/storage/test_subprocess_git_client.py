import subprocess
from unittest.mock import patch, MagicMock
import pytest
from git_repo_jumper.storage.git_client.subprocess import SubprocessGitClient
from git_repo_jumper.domain.errors import ConfiguredGitToolNotFoundError


class TestGetGitStatus:
    def test_returns_invalid_when_path_does_not_exist(self, tmp_path):
        client = SubprocessGitClient()
        result = client.get_git_status(str(tmp_path / 'nonexistent'), None)
        assert result.valid is False
        assert result.error == 'Path does not exist'

    def test_returns_invalid_when_not_a_git_repo(self, tmp_path):
        client = SubprocessGitClient()
        result = client.get_git_status(str(tmp_path), None)
        assert result.valid is False
        assert result.error == 'Not a git repository'

    def test_returns_invalid_on_timeout(self, tmp_path):
        (tmp_path / '.git').mkdir()
        client = SubprocessGitClient()
        with patch(
            'subprocess.run',
            side_effect=subprocess.TimeoutExpired(cmd='git', timeout=5)
        ):
            result = client.get_git_status(str(tmp_path), None)
        assert result.valid is False
        assert result.error == 'Timeout'

    def test_returns_valid_git_info(self, tmp_path):
        (tmp_path / '.git').mkdir()
        client = SubprocessGitClient()

        def mock_run(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if 'rev-parse' in cmd:
                m.stdout = 'main\n'
            elif 'status' in cmd:
                m.stdout = ''
            elif 'rev-list' in cmd:
                m.stdout = '0\t0\n'
            elif 'remote' in cmd:
                m.stdout = 'https://github.com/user/myrepo.git\n'
            else:
                m.stdout = ''
            return m

        with patch('subprocess.run', side_effect=mock_run):
            result = client.get_git_status(str(tmp_path), 'user')

        assert result.valid is True
        assert result.current_branch_name == 'main'


class TestOpenGitTool:
    def test_raises_configured_git_tool_not_found_on_file_not_found(self, tmp_path):
        client = SubprocessGitClient()
        with patch('subprocess.run', side_effect=FileNotFoundError):
            with pytest.raises(ConfiguredGitToolNotFoundError):
                client.open_git_tool(str(tmp_path), 'lazygit')

    def test_raises_configured_git_tool_not_found_on_called_process_error(self, tmp_path):
        client = SubprocessGitClient()
        with patch(
            'subprocess.run',
            side_effect=subprocess.CalledProcessError(1, 'lazygit')
        ):
            with pytest.raises(ConfiguredGitToolNotFoundError):
                client.open_git_tool(str(tmp_path), 'lazygit')

    def test_passes_repo_path_for_lazygit(self, tmp_path):
        client = SubprocessGitClient()
        with patch('subprocess.run') as mock_run:
            client.open_git_tool(str(tmp_path), 'lazygit')
            cmd = mock_run.call_args[0][0]
            assert 'lazygit' in cmd
            assert '-p' in cmd

    def test_unknown_program_uses_dash_p_flag(self, tmp_path):
        client = SubprocessGitClient()
        with patch('subprocess.run') as mock_run:
            client.open_git_tool(str(tmp_path), 'mygit')
            cmd = mock_run.call_args[0][0]
            assert 'mygit' in cmd
            assert '-p' in cmd


class TestGetGithubRepoName:
    def test_returns_dash_when_no_git_dir(self, tmp_path):
        result = SubprocessGitClient._get_github_repo_name(str(tmp_path), 'user')
        assert result == '-'

    def test_returns_dash_for_non_github_remote(self, tmp_path):
        (tmp_path / '.git').mkdir()
        mock = MagicMock(returncode=0, stdout='https://gitlab.com/user/repo.git\n')
        with patch('subprocess.run', return_value=mock):
            result = SubprocessGitClient._get_github_repo_name(str(tmp_path), 'user')
        assert result == '-'

    def test_parses_https_remote_and_strips_username(self, tmp_path):
        (tmp_path / '.git').mkdir()
        mock = MagicMock(
            returncode=0, stdout='https://github.com/user/myrepo.git\n'
        )
        with patch('subprocess.run', return_value=mock):
            result = SubprocessGitClient._get_github_repo_name(str(tmp_path), 'user')
        assert result == 'myrepo'

    def test_parses_ssh_remote_and_strips_username(self, tmp_path):
        (tmp_path / '.git').mkdir()
        mock = MagicMock(returncode=0, stdout='git@github.com:user/myrepo.git\n')
        with patch('subprocess.run', return_value=mock):
            result = SubprocessGitClient._get_github_repo_name(str(tmp_path), 'user')
        assert result == 'myrepo'

    def test_returns_dash_when_remote_command_fails(self, tmp_path):
        (tmp_path / '.git').mkdir()
        mock = MagicMock(returncode=1, stdout='')
        with patch('subprocess.run', return_value=mock):
            result = SubprocessGitClient._get_github_repo_name(str(tmp_path), '')
        assert result == '-'


class TestGenerateStatusSummary:
    def test_clean_repo_returns_checkmark(self, tmp_path):
        def mock_run(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            m.stdout = '' if 'status' in cmd else '0\t0'
            return m

        with patch('subprocess.run', side_effect=mock_run):
            status, changes = SubprocessGitClient._generate_status_summary(tmp_path)

        assert status == '✓'
        assert changes == 0

    def test_dirty_repo_shows_change_count(self, tmp_path):
        def mock_run(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            m.stdout = 'M file1.py\nM file2.py\n' if 'status' in cmd else '0\t0'
            return m

        with patch('subprocess.run', side_effect=mock_run):
            status, changes = SubprocessGitClient._generate_status_summary(tmp_path)

        assert '≠2' in status
        assert changes == 2

    def test_ahead_of_remote_shown_in_status(self, tmp_path):
        def mock_run(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            m.stdout = '' if 'status' in cmd else '0\t3'
            return m

        with patch('subprocess.run', side_effect=mock_run):
            status, _ = SubprocessGitClient._generate_status_summary(tmp_path)

        assert '↑3' in status
