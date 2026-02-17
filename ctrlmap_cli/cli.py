from __future__ import annotations

import argparse
import getpass
from pathlib import Path
from typing import List

from ctrlmap_cli.client import CtrlMapClient
from ctrlmap_cli.config import read_config, write_config
from ctrlmap_cli.exceptions import ConfigError
from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.exporters.governance import GovernanceExporter
from ctrlmap_cli.exporters.policies import PoliciesExporter
from ctrlmap_cli.exporters.procedures import ProceduresExporter
from ctrlmap_cli.exporters.risks import RisksExporter
from ctrlmap_cli.models.config import AppConfig

_SUBDIRS = ("govs", "pols", "pros", "risks")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctrlmap-cli",
        description="Unofficial command-line client for ControlMap data export.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--init",
        metavar="API_URL",
        help="Initialize configuration with the ControlMap API URL.",
    )
    group.add_argument("--copy-all", action="store_true", help="Export all data.")
    group.add_argument("--copy-gov", action="store_true", help="Export governance documents.")
    group.add_argument(
        "--copy-pols", "--copy-pol", dest="copy_pols", action="store_true", help="Export policies.",
    )
    group.add_argument(
        "--copy-pros", "--copy-pro", dest="copy_pros", action="store_true", help="Export procedures.",
    )
    group.add_argument("--copy-risks", action="store_true", help="Export risk register.")
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing files without confirmation.",
    )
    parser.add_argument(
        "--keep-raw-json", action="store_true",
        help="Also write raw JSON files alongside Markdown.",
    )
    return parser


def _run_init(api_url: str) -> None:
    if not api_url.startswith("https://"):
        raise ConfigError("API URL must start with https://")

    bearer_token = getpass.getpass("Enter your bearer token: ")
    if not bearer_token.strip():
        raise ConfigError("Bearer token cannot be empty.")

    tenant_uri = input(
        "Enter your tenant ID "
        "(the subdomain before .app.eu.ctrlmap.com, e.g. 'dime2'): "
    )
    if not tenant_uri.strip():
        raise ConfigError("Tenant ID cannot be empty.")

    config = AppConfig(
        api_url=api_url,
        bearer_token=bearer_token.strip(),
        tenant_uri=tenant_uri.strip(),
    )

    cwd = Path.cwd()
    write_config(cwd, config)

    for subdir in _SUBDIRS:
        (cwd / subdir).mkdir(exist_ok=True)

    print("Configuration saved to .ctrlmap-cli.ini")
    print("Created directories: " + ", ".join(f"{d}/" for d in _SUBDIRS))


def _run_export(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    config = read_config(cwd)
    client = CtrlMapClient(config)

    export_kwargs = {
        "force": args.force,
        "keep_raw_json": args.keep_raw_json,
    }

    exporters: List[BaseExporter] = []
    if args.copy_all or args.copy_gov:
        exporters.append(GovernanceExporter(client, cwd / "govs", **export_kwargs))
    if args.copy_all or args.copy_pols:
        exporters.append(PoliciesExporter(client, cwd / "pols", **export_kwargs))
    if args.copy_all or args.copy_pros:
        exporters.append(ProceduresExporter(client, cwd / "pros", **export_kwargs))
    if args.copy_all or args.copy_risks:
        exporters.append(RisksExporter(client, cwd / "risks", **export_kwargs))

    for exporter in exporters:
        exporter.export()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.init:
        _run_init(args.init)
    elif args.copy_all or args.copy_gov or args.copy_pols or args.copy_pros or args.copy_risks:
        _run_export(args)
    else:
        parser.print_help()
