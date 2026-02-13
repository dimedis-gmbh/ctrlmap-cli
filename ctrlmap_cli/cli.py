from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from ctrlmap_cli.config import write_config
from ctrlmap_cli.exceptions import ConfigError
from ctrlmap_cli.models.config import AppConfig

_SUBDIRS = ("govs", "policies", "procedures", "risks")


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
    group.add_argument("--copy-pols", action="store_true", help="Export policies.")
    group.add_argument("--copy-pros", action="store_true", help="Export procedures.")
    group.add_argument("--copy-risks", action="store_true", help="Export risk register.")
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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.init:
        _run_init(args.init)
    elif args.copy_all or args.copy_gov or args.copy_pols or args.copy_pros or args.copy_risks:
        # Placeholder for export commands (tasks 04-08)
        print("Export not yet implemented.", file=sys.stderr)
        sys.exit(1)
    else:
        parser.print_help()
