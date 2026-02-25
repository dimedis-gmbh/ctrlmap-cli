from __future__ import annotations

import argparse
import getpass
from pathlib import Path
from typing import List, Optional

from ctrlmap_cli import __version__
from ctrlmap_cli.client import CtrlMapClient
from ctrlmap_cli.config import read_config, write_config
from ctrlmap_cli.exceptions import ConfigError
from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.exporters.governance import GovernanceExporter
from ctrlmap_cli.exporters.policies import PoliciesExporter
from ctrlmap_cli.exporters.procedures import ProceduresExporter
from ctrlmap_cli.exporters.risks import RisksExporter
from ctrlmap_cli.exporters.vendors import VendorsExporter
from ctrlmap_cli.models.config import AppConfig

_SUBDIRS = ("govs", "pols", "pros", "risks", "vendors")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctrlmap-cli",
        description="Unofficial command-line client for ControlMap data export.",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--init",
        metavar="API_URL",
        help="Initialize configuration with the ControlMap API URL.",
    )
    group.add_argument("--copy-all", action="store_true", help="Export all data.")
    group.add_argument("--copy-govs", action="store_true", help="Export all governance documents.")
    group.add_argument("--copy-gov", metavar="CODE", help="Export a single governance document by code.")
    group.add_argument("--copy-pols", action="store_true", help="Export all policies.")
    group.add_argument("--copy-pol", metavar="CODE", help="Export a single policy by code.")
    group.add_argument("--copy-pros", action="store_true", help="Export all procedures.")
    group.add_argument("--copy-pro", metavar="CODE", help="Export a single procedure by code.")
    group.add_argument("--copy-risks", action="store_true", help="Export all risks.")
    group.add_argument("--copy-risk", metavar="CODE", help="Export a single risk by code.")
    group.add_argument("--copy-vendors", action="store_true", help="Export all vendors.")
    group.add_argument("--copy-vendor", metavar="CODE", help="Export a single vendor by code.")
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

    # Single-item exports
    _SINGLE_EXPORTS: List[tuple] = [
        (args.copy_gov, GovernanceExporter, "govs"),
        (args.copy_pol, PoliciesExporter, "pols"),
        (args.copy_pro, ProceduresExporter, "pros"),
        (args.copy_risk, RisksExporter, "risks"),
        (args.copy_vendor, VendorsExporter, "vendors"),
    ]

    for code, exporter_cls, subdir in _SINGLE_EXPORTS:
        if code is not None:
            exporter: BaseExporter = exporter_cls(client, cwd / subdir, **export_kwargs)
            exporter.export_single(code)
            return

    # Bulk exports
    exporters: List[BaseExporter] = []
    if args.copy_all or args.copy_govs:
        exporters.append(GovernanceExporter(client, cwd / "govs", **export_kwargs))
    if args.copy_all or args.copy_pols:
        exporters.append(PoliciesExporter(client, cwd / "pols", **export_kwargs))
    if args.copy_all or args.copy_pros:
        exporters.append(ProceduresExporter(client, cwd / "pros", **export_kwargs))
    if args.copy_all or args.copy_risks:
        exporters.append(RisksExporter(client, cwd / "risks", **export_kwargs))
    if args.copy_all or args.copy_vendors:
        exporters.append(VendorsExporter(client, cwd / "vendors", **export_kwargs))

    for exporter in exporters:
        exporter.export()


def _has_export_flag(args: argparse.Namespace) -> bool:
    """Check whether any export flag was provided."""
    return bool(
        args.copy_all or args.copy_govs or args.copy_gov
        or args.copy_pols or args.copy_pol
        or args.copy_pros or args.copy_pro
        or args.copy_risks or args.copy_risk
        or args.copy_vendors or args.copy_vendor
    )


def _get_single_code(args: argparse.Namespace) -> Optional[str]:
    """Return the single-item code if a singular flag was used, else None."""
    for attr in ("copy_gov", "copy_pol", "copy_pro", "copy_risk", "copy_vendor"):
        val = getattr(args, attr, None)
        if val is not None:
            return val
    return None


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.init:
        _run_init(args.init)
    elif _has_export_flag(args):
        _run_export(args)
    else:
        parser.print_help()
