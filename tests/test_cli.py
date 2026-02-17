from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ctrlmap_cli.cli import main, _SUBDIRS
from ctrlmap_cli.config import CONFIG_FILENAME, read_config
from ctrlmap_cli.exceptions import ConfigError


class TestNoArgs:
    def test_no_args_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("sys.argv", ["ctrlmap-cli"]):
            main()
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()


class TestInit:
    def test_init_creates_config_and_dirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["ctrlmap-cli", "--init", "https://api.eu.ctrlmap.com/"]), \
             patch("ctrlmap_cli.cli.getpass.getpass", return_value="my-token"), \
             patch("builtins.input", return_value="dime2"):
            main()

        assert (tmp_path / CONFIG_FILENAME).is_file()
        for subdir in _SUBDIRS:
            assert (tmp_path / subdir).is_dir()

        config = read_config(tmp_path)
        assert config.api_url == "https://api.eu.ctrlmap.com/"
        assert config.bearer_token == "my-token"
        assert config.tenant_uri == "dime2"

    def test_init_prints_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["ctrlmap-cli", "--init", "https://api.eu.ctrlmap.com/"]), \
             patch("ctrlmap_cli.cli.getpass.getpass", return_value="tok"), \
             patch("builtins.input", return_value="t1"):
            main()
        captured = capsys.readouterr()
        assert "Configuration saved" in captured.out
        assert "Created directories" in captured.out

    def test_init_url_normalized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["ctrlmap-cli", "--init", "https://api.eu.ctrlmap.com"]), \
             patch("ctrlmap_cli.cli.getpass.getpass", return_value="tok"), \
             patch("builtins.input", return_value="t1"):
            main()
        config = read_config(tmp_path)
        assert config.api_url == "https://api.eu.ctrlmap.com/"

    def test_init_existing_dirs_no_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "govs").mkdir()
        with patch("sys.argv", ["ctrlmap-cli", "--init", "https://api.eu.ctrlmap.com/"]), \
             patch("ctrlmap_cli.cli.getpass.getpass", return_value="tok"), \
             patch("builtins.input", return_value="t1"):
            main()
        assert (tmp_path / "govs").is_dir()


class TestInitErrors:
    def test_invalid_url_scheme(self) -> None:
        with patch("sys.argv", ["ctrlmap-cli", "--init", "http://api.example.com/"]):
            with pytest.raises(ConfigError, match="must start with https://"):
                main()

    def test_empty_bearer_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["ctrlmap-cli", "--init", "https://api.example.com/"]), \
             patch("ctrlmap_cli.cli.getpass.getpass", return_value=""):
            with pytest.raises(ConfigError, match="Bearer token cannot be empty"):
                main()

    def test_empty_tenant_uri(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["ctrlmap-cli", "--init", "https://api.example.com/"]), \
             patch("ctrlmap_cli.cli.getpass.getpass", return_value="tok"), \
             patch("builtins.input", return_value=""):
            with pytest.raises(ConfigError, match="Tenant ID cannot be empty"):
                main()


class TestCopyFlagsRequireConfig:
    @pytest.mark.parametrize("flag", [
        "--copy-all", "--copy-gov", "--copy-pols", "--copy-pol",
        "--copy-pros", "--copy-pro", "--copy-risks", "--copy-risk",
    ])
    def test_copy_flags_fail_without_config(
        self, flag: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["ctrlmap-cli", flag]):
            with pytest.raises(ConfigError):
                main()


class TestInitSubprocess:
    def test_python_m_init_creates_config_and_dirs(self, tmp_path: Path) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root)
        completed = subprocess.run(
            [sys.executable, "-m", "ctrlmap_cli", "--init", "https://api.eu.ctrlmap.com/"],
            cwd=tmp_path,
            env=env,
            input="token-from-stdin\ndime2\n",
            text=True,
            capture_output=True,
            check=False,
        )

        assert completed.returncode == 0
        assert (tmp_path / CONFIG_FILENAME).is_file()
        for subdir in _SUBDIRS:
            assert (tmp_path / subdir).is_dir()

        cfg = read_config(tmp_path)
        assert cfg.api_url == "https://api.eu.ctrlmap.com/"
        assert cfg.bearer_token == "token-from-stdin"
        assert cfg.tenant_uri == "dime2"
