from __future__ import annotations

import configparser
from pathlib import Path

from ctrlmap_cli.exceptions import ConfigError
from ctrlmap_cli.models.config import AppConfig

CONFIG_FILENAME = ".ctrlmap-cli.ini"
_SECTION = "ctrlmap"
_REQUIRED_KEYS = ("api_url", "bearer_token", "tenant_uri")


def config_exists(directory: Path) -> bool:
    return (directory / CONFIG_FILENAME).is_file()


def write_config(directory: Path, config: AppConfig) -> None:
    cp = configparser.ConfigParser()
    cp[_SECTION] = {
        "api_url": config.api_url,
        "bearer_token": config.bearer_token,
        "tenant_uri": config.tenant_uri,
    }
    path = directory / CONFIG_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        cp.write(f)


def read_config(directory: Path) -> AppConfig:
    path = directory / CONFIG_FILENAME
    if not path.is_file():
        raise ConfigError(
            "Configuration not found. Run ctrlmap-cli --init first."
        )

    cp = configparser.ConfigParser()
    try:
        cp.read(str(path), encoding="utf-8")
    except configparser.Error as exc:
        raise ConfigError(
            f"Invalid configuration format in {CONFIG_FILENAME}. "
            "Run ctrlmap-cli --init to reconfigure."
        ) from exc

    if not cp.has_section(_SECTION):
        raise ConfigError(
            f"Invalid configuration: missing [{_SECTION}] section in {CONFIG_FILENAME}."
        )

    for key in _REQUIRED_KEYS:
        if not cp.has_option(_SECTION, key) or not cp.get(_SECTION, key).strip():
            raise ConfigError(
                f"Invalid configuration: missing or empty '{key}' in {CONFIG_FILENAME}. "
                "Run ctrlmap-cli --init to reconfigure."
            )

    return AppConfig(
        api_url=cp.get(_SECTION, "api_url"),
        bearer_token=cp.get(_SECTION, "bearer_token"),
        tenant_uri=cp.get(_SECTION, "tenant_uri"),
    )
