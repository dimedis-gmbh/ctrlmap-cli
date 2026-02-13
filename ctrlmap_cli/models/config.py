from __future__ import annotations

from dataclasses import dataclass

from ctrlmap_cli.exceptions import ConfigError


@dataclass
class AppConfig:
    api_url: str
    bearer_token: str
    tenant_uri: str

    def __post_init__(self) -> None:
        if not self.api_url:
            raise ConfigError("API URL cannot be empty.")
        if not self.api_url.endswith("/"):
            self.api_url = self.api_url + "/"
        if not self.bearer_token:
            raise ConfigError("Bearer token cannot be empty.")
        if not self.tenant_uri:
            raise ConfigError("Tenant ID cannot be empty.")
