from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from ctrlmap_cli.client import CtrlMapClient
from ctrlmap_cli.exceptions import ApiError, AuthenticationError, CtrlMapError
from ctrlmap_cli.models.config import AppConfig


def _make_client() -> CtrlMapClient:
    config = AppConfig(
        api_url="https://api.eu.ctrlmap.com/",
        bearer_token="test-token",
        tenant_uri="dime2",
    )
    return CtrlMapClient(config)


def _mock_response(status_code: int = 200, json_data: object = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    return resp


class TestClientHeaders:
    def test_session_headers(self) -> None:
        client = _make_client()
        headers = client._session.headers
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["x-authprovider"] == "cmapjwt"
        assert headers["x-tenanturi"] == "dime2"
        assert "ctrlmap-cli/" in headers["User-Agent"]


class TestGet:
    def test_get_success(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(200, {"id": 1, "name": "test"})
        with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
            result = client.get("procedure/37")
        mock_req.assert_called_once_with(
            "GET", "https://api.eu.ctrlmap.com/procedure/37", params=None,
        )
        assert result == {"id": 1, "name": "test"}

    def test_get_with_params(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(200, [])
        with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
            client.get("procedure/versions", params={"procedureid": "37"})
        mock_req.assert_called_once_with(
            "GET", "https://api.eu.ctrlmap.com/procedure/versions",
            params={"procedureid": "37"},
        )

    def test_get_strips_leading_slash(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(200, {})
        with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
            client.get("/procedure/37")
        mock_req.assert_called_once_with(
            "GET", "https://api.eu.ctrlmap.com/procedure/37", params=None,
        )


class TestPost:
    def test_post_success(self) -> None:
        client = _make_client()
        body = {"startpos": 0, "pagesize": 500, "rules": []}
        mock_resp = _mock_response(200, [{"id": 1}])
        with patch.object(client._session, "request", return_value=mock_resp) as mock_req:
            result = client.post("procedures", json=body)
        mock_req.assert_called_once_with(
            "POST", "https://api.eu.ctrlmap.com/procedures", json=body,
        )
        assert result == [{"id": 1}]


class TestErrorHandling:
    def test_401_raises_authentication_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(401)
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(AuthenticationError, match="bearer token may have expired"):
                client.get("procedure/1")

    def test_403_raises_authentication_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(403)
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(AuthenticationError, match="bearer token may have expired"):
                client.get("procedure/1")

    def test_404_raises_api_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(404)
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(ApiError, match="Resource not found: procedure/999"):
                client.get("procedure/999")

    def test_500_raises_api_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(500)
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(ApiError, match="server error \\(500\\)"):
                client.get("procedure/1")

    def test_502_raises_api_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(502)
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(ApiError, match="server error \\(502\\)"):
                client.get("procedure/1")

    def test_connection_error_raises_api_error(self) -> None:
        client = _make_client()
        with patch.object(
            client._session, "request", side_effect=requests.ConnectionError("refused"),
        ):
            with pytest.raises(ApiError, match="Cannot connect to"):
                client.get("procedure/1")

    def test_request_exception_raises_api_error(self) -> None:
        client = _make_client()
        with patch.object(
            client._session, "request", side_effect=requests.RequestException("timeout"),
        ):
            with pytest.raises(ApiError, match="Cannot connect to"):
                client.get("procedure/1")

    def test_unmapped_4xx_raises_api_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(400)
        mock_resp.raise_for_status.side_effect = requests.HTTPError("400 bad request")
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(ApiError, match="request failed \\(400\\) for procedure/1"):
                client.get("procedure/1")

    def test_invalid_json_raises_api_error(self) -> None:
        client = _make_client()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError("invalid json")
        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises(ApiError, match="Invalid response from ControlMap API for procedure/1"):
                client.get("procedure/1")

    def test_error_types_are_ctrlmap_errors(self) -> None:
        assert issubclass(ApiError, CtrlMapError)
        assert issubclass(AuthenticationError, ApiError)
