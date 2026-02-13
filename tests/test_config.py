from __future__ import annotations

import pytest

from ctrlmap_cli.config import (
    CONFIG_FILENAME,
    config_exists,
    read_config,
    write_config,
)
from ctrlmap_cli.exceptions import ConfigError
from ctrlmap_cli.models.config import AppConfig


def _make_config(
    api_url: str = "https://api.eu.ctrlmap.com/",
    bearer_token: str = "test-token-123",
    tenant_uri: str = "dime2",
) -> AppConfig:
    return AppConfig(
        api_url=api_url,
        bearer_token=bearer_token,
        tenant_uri=tenant_uri,
    )


class TestAppConfig:
    def test_valid_config(self) -> None:
        cfg = _make_config()
        assert cfg.api_url == "https://api.eu.ctrlmap.com/"
        assert cfg.bearer_token == "test-token-123"
        assert cfg.tenant_uri == "dime2"

    def test_api_url_trailing_slash_added(self) -> None:
        cfg = _make_config(api_url="https://api.eu.ctrlmap.com")
        assert cfg.api_url == "https://api.eu.ctrlmap.com/"

    def test_api_url_trailing_slash_kept(self) -> None:
        cfg = _make_config(api_url="https://api.eu.ctrlmap.com/")
        assert cfg.api_url == "https://api.eu.ctrlmap.com/"

    def test_empty_api_url_raises(self) -> None:
        with pytest.raises(ConfigError, match="API URL cannot be empty"):
            _make_config(api_url="")

    def test_empty_bearer_token_raises(self) -> None:
        with pytest.raises(ConfigError, match="Bearer token cannot be empty"):
            _make_config(bearer_token="")

    def test_empty_tenant_uri_raises(self) -> None:
        with pytest.raises(ConfigError, match="Tenant ID cannot be empty"):
            _make_config(tenant_uri="")


class TestConfigExists:
    def test_exists_false(self, tmp_path: object) -> None:
        assert config_exists(tmp_path) is False  # type: ignore[arg-type]

    def test_exists_true(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        (p / CONFIG_FILENAME).write_text("[ctrlmap]\n", encoding="utf-8")
        assert config_exists(p) is True


class TestWriteReadRoundTrip:
    def test_round_trip(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        original = _make_config()
        write_config(p, original)

        assert (p / CONFIG_FILENAME).is_file()

        loaded = read_config(p)
        assert loaded.api_url == original.api_url
        assert loaded.bearer_token == original.bearer_token
        assert loaded.tenant_uri == original.tenant_uri

    def test_round_trip_url_normalized(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        original = _make_config(api_url="https://api.eu.ctrlmap.com")
        write_config(p, original)

        loaded = read_config(p)
        assert loaded.api_url == "https://api.eu.ctrlmap.com/"


class TestReadConfigErrors:
    def test_missing_file(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        with pytest.raises(ConfigError, match="Configuration not found"):
            read_config(p)

    def test_missing_section(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        (p / CONFIG_FILENAME).write_text("[wrong]\nkey = val\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="missing \\[ctrlmap\\] section"):
            read_config(p)

    def test_missing_key(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        (p / CONFIG_FILENAME).write_text(
            "[ctrlmap]\napi_url = https://x.com/\nbearer_token = tok\n",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="missing or empty 'tenant_uri'"):
            read_config(p)

    def test_empty_value(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        (p / CONFIG_FILENAME).write_text(
            "[ctrlmap]\napi_url = https://x.com/\nbearer_token =\ntenant_uri = t\n",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="missing or empty 'bearer_token'"):
            read_config(p)

    def test_malformed_ini_syntax(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(str(tmp_path))
        (p / CONFIG_FILENAME).write_text(
            "not-an-ini\napi_url = https://x.com/\n",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="Invalid configuration format"):
            read_config(p)
