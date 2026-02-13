from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.exporters.governance import GovernanceExporter
from ctrlmap_cli.exporters.policies import PoliciesExporter
from ctrlmap_cli.exporters.procedures import ProceduresExporter
from ctrlmap_cli.exporters.risks import RisksExporter
from ctrlmap_cli.models.config import AppConfig


def _raw_procedure_doc(doc_id: int, code: str, name: str = "Title") -> dict:
    return {
        "id": doc_id,
        "procedureCode": code,
        "name": f" {name} ",
        "description": "body text",
        "status": {"name": "Approved"},
    }


def _raw_risk_doc(doc_id: int, code: str, name: str = "Risk") -> dict:
    return {
        "id": doc_id,
        "riskCode": code,
        "name": f" {name} ",
        "description": "risk body",
        "status": {"name": "Open"},
        "severity": {"name": "High"},
    }


class TestBaseExporter:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseExporter(MagicMock(), Path("/tmp/test"))  # type: ignore[abstract]

    def test_ensure_output_dir_creates_directory(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path / "nested" / "dir")
        exporter._ensure_output_dir()
        assert (tmp_path / "nested" / "dir").is_dir()

    def test_log_prints_to_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path)
        exporter._log("hello world")
        assert "hello world" in capsys.readouterr().out

    def test_write_document_creates_all_formats(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path)
        exporter._ensure_output_dir()
        data = {"title": "Test Doc", "body": "Content here.", "status": "active"}
        exporter._write_document("test-doc", data)

        assert (tmp_path / "test-doc.md").exists()
        assert (tmp_path / "test-doc.json").exists()
        assert (tmp_path / "test-doc.yaml").exists()

    def test_write_document_with_dataclass(self, tmp_path: Path) -> None:
        @dataclass
        class SampleDoc:
            title: str
            body: str
            version: int

        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path)
        exporter._ensure_output_dir()
        exporter._write_document("sample", SampleDoc(title="DC Title", body="DC body.", version=2))

        parsed_json = json.loads((tmp_path / "sample.json").read_text())
        assert parsed_json["version"] == 2

        parsed_yaml = yaml.safe_load((tmp_path / "sample.yaml").read_text())
        assert parsed_yaml["title"] == "DC Title"


class TestGovernanceExporter:
    def test_export_calls_expected_endpoint_and_rule(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = []

        exporter = GovernanceExporter(client, tmp_path / "govs")
        exporter.export()

        call_args = client.get.call_args
        assert call_args[0][0] == "/procedures"
        assert call_args[1]["params"]["type"] == "governance"

    def test_export_writes_documents(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = [_raw_procedure_doc(1, "GOV-1"), _raw_procedure_doc(2, "GOV-2")]

        exporter = GovernanceExporter(client, tmp_path / "govs")
        exporter.export()

        for code in ("GOV-1", "GOV-2"):
            assert (tmp_path / "govs" / f"{code}.md").exists()
            assert (tmp_path / "govs" / f"{code}.json").exists()
            assert (tmp_path / "govs" / f"{code}.yaml").exists()


class TestPoliciesExporter:
    def test_export_calls_expected_endpoint_and_rule(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = []

        exporter = PoliciesExporter(client, tmp_path / "policies")
        exporter.export()

        call_args = client.get.call_args
        assert call_args[0][0] == "/procedures"
        assert call_args[1]["params"]["type"] == "policy"

    def test_export_writes_documents(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = [_raw_procedure_doc(1, "POL-1"), _raw_procedure_doc(2, "POL-2")]

        exporter = PoliciesExporter(client, tmp_path / "policies")
        exporter.export()

        for code in ("POL-1", "POL-2"):
            assert (tmp_path / "policies" / f"{code}.md").exists()
            assert (tmp_path / "policies" / f"{code}.json").exists()
            assert (tmp_path / "policies" / f"{code}.yaml").exists()


class TestProceduresExporter:
    def test_export_calls_expected_endpoint_and_rule(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = []

        exporter = ProceduresExporter(client, tmp_path / "procedures")
        exporter.export()

        call_args = client.get.call_args
        assert call_args[0][0] == "/procedures"
        assert call_args[1]["params"]["type"] == "procedure"

    def test_export_writes_documents(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = [_raw_procedure_doc(1, "PRO-1"), _raw_procedure_doc(2, "PRO-2")]

        exporter = ProceduresExporter(client, tmp_path / "procedures")
        exporter.export()

        for code in ("PRO-1", "PRO-2"):
            assert (tmp_path / "procedures" / f"{code}.md").exists()
            assert (tmp_path / "procedures" / f"{code}.json").exists()
            assert (tmp_path / "procedures" / f"{code}.yaml").exists()


class TestRisksExporter:
    def test_export_calls_expected_endpoint(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = []

        exporter = RisksExporter(client, tmp_path / "risks")
        exporter.export()

        client.get.assert_called_once_with("/risks")

    def test_export_writes_documents(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = [_raw_risk_doc(1, "RISK-1"), _raw_risk_doc(2, "RISK-2")]

        exporter = RisksExporter(client, tmp_path / "risks")
        exporter.export()

        for code in ("RISK-1", "RISK-2"):
            assert (tmp_path / "risks" / f"{code}.md").exists()
            assert (tmp_path / "risks" / f"{code}.json").exists()
            assert (tmp_path / "risks" / f"{code}.yaml").exists()


class TestExporterProgress:
    @pytest.mark.parametrize(
        "exporter_cls, method_name, payload, text",
        [
            (GovernanceExporter, "get", [_raw_procedure_doc(1, "GOV-1")], "Exporting governance"),
            (PoliciesExporter, "get", [_raw_procedure_doc(1, "POL-1")], "Exporting policies"),
            (ProceduresExporter, "get", [_raw_procedure_doc(1, "PRO-1")], "Exporting procedures"),
            (RisksExporter, "get", [_raw_risk_doc(1, "RISK-1")], "Exporting risks"),
        ],
    )
    def test_progress_log_contains_done_count(
        self,
        exporter_cls: type,
        method_name: str,
        payload: list,
        text: str,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock()
        getattr(client, method_name).return_value = payload

        exporter = exporter_cls(client, tmp_path / "out")
        exporter.export()

        out = capsys.readouterr().out
        assert text in out
        assert "done (1 documents)" in out


class TestCliExportWiring:
    @staticmethod
    def _setup_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> MagicMock:
        monkeypatch.chdir(tmp_path)
        config = AppConfig(
            api_url="https://api.eu.ctrlmap.com/",
            bearer_token="token",
            tenant_uri="dime2",
        )
        monkeypatch.setattr("ctrlmap_cli.cli.read_config", MagicMock(return_value=config))
        client = MagicMock(name="client")
        monkeypatch.setattr("ctrlmap_cli.cli.CtrlMapClient", MagicMock(return_value=client))
        return client

    def test_copy_gov_uses_governance_output_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        gov_instance = MagicMock()
        gov_cls = MagicMock(return_value=gov_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", gov_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.PoliciesExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", MagicMock())

        with patch("sys.argv", ["ctrlmap-cli", "--copy-gov"]):
            from ctrlmap_cli.cli import main
            main()

        gov_cls.assert_called_once_with(client, tmp_path / "govs")
        gov_instance.export.assert_called_once()

    def test_copy_all_runs_all_exporters_with_expected_dirs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)

        gov_instance = MagicMock()
        pol_instance = MagicMock()
        pro_instance = MagicMock()
        risk_instance = MagicMock()

        gov_cls = MagicMock(return_value=gov_instance)
        pol_cls = MagicMock(return_value=pol_instance)
        pro_cls = MagicMock(return_value=pro_instance)
        risk_cls = MagicMock(return_value=risk_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", gov_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.PoliciesExporter", pol_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", pro_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", risk_cls)

        with patch("sys.argv", ["ctrlmap-cli", "--copy-all"]):
            from ctrlmap_cli.cli import main
            main()

        gov_cls.assert_called_once_with(client, tmp_path / "govs")
        pol_cls.assert_called_once_with(client, tmp_path / "policies")
        pro_cls.assert_called_once_with(client, tmp_path / "procedures")
        risk_cls.assert_called_once_with(client, tmp_path / "risks")

        gov_instance.export.assert_called_once()
        pol_instance.export.assert_called_once()
        pro_instance.export.assert_called_once()
        risk_instance.export.assert_called_once()
