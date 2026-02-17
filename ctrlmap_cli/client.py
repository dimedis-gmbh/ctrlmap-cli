from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from ctrlmap_cli import __version__
from ctrlmap_cli.exceptions import ApiError, AuthenticationError
from ctrlmap_cli.models.config import AppConfig


class CtrlMapClient:
    _POLICIES_LIST_BODY: Dict[str, Any] = {
        "startpos": 0,
        "pagesize": 1000,
        "sortby": None,
        "rules": [
            {"field": "type", "operator": "=", "value": "policy"},
        ],
    }

    def __init__(self, config: AppConfig) -> None:
        self._base_url = config.api_url
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.bearer_token}",
            "x-authprovider": "cmapjwt",
            "x-tenanturi": config.tenant_uri,
            "User-Agent": f"ctrlmap-cli/{__version__}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def get(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("POST", path, json=json)

    def list_policies(self) -> Any:
        return self.post("/policies", json=self._POLICIES_LIST_BODY)

    def get_policy(self, policy_id: int) -> Any:
        return self.get(f"/policy/{policy_id}")

    _PROCEDURES_LIST_BODY: Dict[str, Any] = {
        "startpos": 0,
        "pagesize": 500,
        "sortby": None,
        "rules": [
            {"field": "type", "operator": "=", "value": "procedure"},
        ],
    }

    def list_procedures(self) -> Any:
        return self.post("/procedures", json=self._PROCEDURES_LIST_BODY)

    def get_procedure(self, procedure_id: int) -> Any:
        return self.get(f"/procedure/{procedure_id}")

    def get_procedure_controls(self, procedure_id: int) -> Any:
        return self.get(f"/procedure/{procedure_id}/controls")

    def get_procedure_requirements(self, procedure_id: int) -> Any:
        return self.get(f"/procedure/{procedure_id}/requirements")

    _RISKS_LIST_BODY: Dict[str, Any] = {
        "startpos": 0,
        "pagesize": 500,
        "rules": [],
    }

    def list_risks(self) -> Any:
        return self.post("/risks", json=self._RISKS_LIST_BODY)

    def get_risk(self, risk_id: int) -> Any:
        return self.get(f"/risks/{risk_id}")

    def get_risk_areas(self, risk_id: int) -> Any:
        return self.get("/riskarea", params={"riskId": str(risk_id)})

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        normalized_path = path.lstrip("/")
        url = self._base_url + normalized_path
        try:
            response = self._session.request(method, url, **kwargs)
        except requests.ConnectionError as exc:
            raise ApiError(
                f"Cannot connect to {self._base_url}. "
                "Check your network connection and API URL."
            ) from exc
        except requests.RequestException as exc:
            raise ApiError(
                f"Cannot connect to {self._base_url}. "
                "Check your network connection and API URL."
            ) from exc

        if response.status_code in (401, 403):
            raise AuthenticationError(
                "Authentication failed. Your bearer token may have expired. "
                "Run ctrlmap-cli --init to set a new token."
            )
        if response.status_code == 404:
            raise ApiError(
                f"Resource not found: {normalized_path}. "
                "The ControlMap API may have changed."
            )
        if response.status_code >= 500:
            raise ApiError(
                f"ControlMap server error ({response.status_code}). "
                "Please try again later."
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ApiError(
                f"ControlMap API request failed ({response.status_code}) for {normalized_path}. "
                "Please verify the request and try again."
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(
                f"Invalid response from ControlMap API for {normalized_path}. Expected JSON data."
            ) from exc
