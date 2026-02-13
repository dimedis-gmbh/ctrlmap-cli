from __future__ import annotations

import importlib
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

import ctrlmap_cli.__main__ as app_main
import ctrlmap_cli.cli as cli
from ctrlmap_cli import __version__
from ctrlmap_cli.exceptions import CtrlMapError


def test_version_is_defined() -> None:
    assert __version__ == "0.1.0"


def test_cli_main_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    from unittest.mock import patch
    with patch("sys.argv", ["ctrlmap-cli"]):
        cli.main()
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()


@pytest.mark.parametrize(
    "module_name",
    [
        "ctrlmap_cli.config",
        "ctrlmap_cli.client",
        "ctrlmap_cli.exporters",
        "ctrlmap_cli.formatters",
        "ctrlmap_cli.models",
    ],
)
def test_scaffolding_modules_are_importable(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None


def test_main_calls_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_cli_main() -> None:
        called["value"] = True

    monkeypatch.setattr(app_main, "cli_main", fake_cli_main)
    app_main.main()
    assert called["value"] is True


def test_main_exits_on_ctrlmap_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def raise_ctrlmap_error() -> None:
        raise CtrlMapError("boom")

    monkeypatch.setattr(app_main, "cli_main", raise_ctrlmap_error)

    with pytest.raises(SystemExit) as raised:
        app_main.main()

    captured = capsys.readouterr()
    assert raised.value.code == 1
    assert captured.err.strip() == "Error: boom"


def test_main_exits_on_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def raise_keyboard_interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(app_main, "cli_main", raise_keyboard_interrupt)

    with pytest.raises(SystemExit) as raised:
        app_main.main()

    captured = capsys.readouterr()
    assert raised.value.code == 130
    assert captured.out == "\n"
    assert captured.err == ""


def test_python_m_entrypoint_executes_main(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"value": 0}

    def fake_cli_main() -> None:
        call_count["value"] += 1

    monkeypatch.setattr(cli, "main", fake_cli_main)
    module_path = Path(app_main.__file__).resolve()
    runpy.run_path(str(module_path), run_name="__main__")
    assert call_count["value"] == 1


def test_python_m_ctrlmap_cli_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "ctrlmap_cli"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "usage:" in completed.stdout.lower()
