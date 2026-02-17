from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.exporters.policies import PoliciesExporter
from ctrlmap_cli.exporters.procedures import ProceduresExporter
from ctrlmap_cli.exporters.risks import RisksExporter
from ctrlmap_cli.models.config import AppConfig


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

    def test_write_document_creates_md_and_yaml_by_default(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path)
        exporter._ensure_output_dir()
        data = {"title": "Test Doc", "body": "Content here.", "status": "active"}
        exporter._write_document("test-doc", data)

        assert (tmp_path / "test-doc.md").exists()
        assert not (tmp_path / "test-doc.json").exists()
        assert (tmp_path / "test-doc.yaml").exists()

    def test_write_document_creates_json_with_keep_raw_json(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path, keep_raw_json=True)
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

        exporter = Concrete(MagicMock(), tmp_path, keep_raw_json=True)
        exporter._ensure_output_dir()
        exporter._write_document("sample", SampleDoc(title="DC Title", body="DC body.", version=2))

        parsed_json = json.loads((tmp_path / "sample.json").read_text())
        assert parsed_json["version"] == 2

        parsed_yaml = yaml.safe_load((tmp_path / "sample.yaml").read_text())
        assert parsed_yaml["title"] == "DC Title"


class TestBaseExporterOverwrite:
    def test_should_write_returns_true_for_new_file(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        exporter = Concrete(MagicMock(), tmp_path)
        assert exporter._should_write(tmp_path / "new-file.md") is True

    def test_should_write_returns_true_with_force(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        existing = tmp_path / "existing.md"
        existing.write_text("content")

        exporter = Concrete(MagicMock(), tmp_path, force=True)
        assert exporter._should_write(existing) is True

    def test_should_write_prompts_and_respects_no(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        existing = tmp_path / "existing.md"
        existing.write_text("content")

        exporter = Concrete(MagicMock(), tmp_path)
        with patch("builtins.input", return_value="n"):
            assert exporter._should_write(existing) is False

    def test_should_write_prompts_and_respects_yes(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        existing = tmp_path / "existing.md"
        existing.write_text("content")

        exporter = Concrete(MagicMock(), tmp_path)
        with patch("builtins.input", return_value="y"):
            assert exporter._should_write(existing) is True

    def test_should_write_all_sets_overwrite_all(self, tmp_path: Path) -> None:
        class Concrete(BaseExporter):
            def export(self) -> None:
                pass

        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("a")
        f2.write_text("b")

        exporter = Concrete(MagicMock(), tmp_path)
        with patch("builtins.input", return_value="a") as mock_input:
            assert exporter._should_write(f1) is True
            assert exporter._should_write(f2) is True

        # Only prompted once — second call uses _overwrite_all
        assert mock_input.call_count == 1


class TestPoliciesExporter:
    """Basic smoke tests; see test_policies.py for comprehensive coverage."""

    @staticmethod
    def _setup_client(list_items: list, details: dict) -> MagicMock:
        client = MagicMock()
        client.list_policies.return_value = list_items
        client.get_policy.side_effect = lambda policy_id: details.get(policy_id, {})
        return client

    @staticmethod
    def _make_detail(doc_id: int = 1, code: str = "POL-1") -> dict:
        from urllib.parse import quote
        return {
            "id": doc_id,
            "policyCode": code,
            "name": " Title ",
            "status": {"name": "Approved"},
            "majorVersion": 1,
            "minorVersion": 0,
            "owner": {"fullname": "Owner"},
            "approver": {"fullname": "Approver"},
            "policyContributors": [],
            "dataClassification": "",
            "reviewDate": None,
            "updatedate": None,
            "sections": [{
                "id": 1,
                "title": "Section",
                "description": quote(quote("<p>Body.</p>", safe=""), safe=""),
            }],
        }

    def test_export_calls_expected_endpoint_and_rule(self, tmp_path: Path) -> None:
        client = self._setup_client(list_items=[], details={})

        PoliciesExporter(client, tmp_path / "pols").export()

        client.list_policies.assert_called_once_with()

    def test_export_writes_md_only_by_default(self, tmp_path: Path) -> None:
        detail = self._make_detail(1, "POL-1")
        client = self._setup_client([{"id": 1}], {1: detail})

        PoliciesExporter(client, tmp_path / "pols").export()

        assert (tmp_path / "pols" / "POL-1.md").exists()
        assert not (tmp_path / "pols" / "POL-1.json").exists()

    def test_export_writes_json_with_keep_raw_json(self, tmp_path: Path) -> None:
        detail = self._make_detail(1, "POL-1")
        client = self._setup_client([{"id": 1}], {1: detail})

        PoliciesExporter(client, tmp_path / "pols", keep_raw_json=True).export()

        assert (tmp_path / "pols" / "POL-1.md").exists()
        assert (tmp_path / "pols" / "POL-1.json").exists()


class TestProceduresExporter:
    """Basic smoke tests; see test_procedures.py for comprehensive coverage."""

    @staticmethod
    def _setup_client(list_items: list, details: dict) -> MagicMock:
        client = MagicMock()
        client.list_procedures.return_value = list_items
        client.get_procedure.side_effect = lambda pid: details.get(pid, {})
        client.get_procedure_controls.return_value = []
        client.get_procedure_requirements.return_value = []
        return client

    @staticmethod
    def _make_detail(doc_id: int = 1, code: str = "PRO-1") -> dict:
        from urllib.parse import quote
        return {
            "id": doc_id,
            "procedureCode": code,
            "name": " Title ",
            "status": {"name": "Approved"},
            "majorVersion": 1,
            "minorVersion": 0,
            "owner": {"fullname": "Owner"},
            "approver": {"fullname": "Approver"},
            "procedureContributors": [],
            "dataClassification": "",
            "frequency": {"name": "Annual"},
            "reviewDate": None,
            "updatedate": None,
            "description": quote(quote("<p>Body.</p>", safe=""), safe=""),
        }

    def test_export_calls_expected_endpoint(self, tmp_path: Path) -> None:
        client = self._setup_client(list_items=[], details={})

        ProceduresExporter(client, tmp_path / "pros").export()

        client.list_procedures.assert_called_once_with()

    def test_export_writes_md_only_by_default(self, tmp_path: Path) -> None:
        detail = self._make_detail(1, "PRO-1")
        client = self._setup_client([{"id": 1}], {1: detail})

        ProceduresExporter(client, tmp_path / "pros").export()

        assert (tmp_path / "pros" / "PRO-1.md").exists()
        assert not (tmp_path / "pros" / "PRO-1.json").exists()
        assert not list((tmp_path / "pros").glob("*.yaml"))

    def test_export_writes_json_with_keep_raw_json(self, tmp_path: Path) -> None:
        detail = self._make_detail(1, "PRO-1")
        client = self._setup_client([{"id": 1}], {1: detail})

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        assert (tmp_path / "pros" / "PRO-1.md").exists()
        assert (tmp_path / "pros" / "PRO-1.json").exists()


class TestRisksExporter:
    def test_export_calls_expected_endpoint(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = []

        exporter = RisksExporter(client, tmp_path / "risks")
        exporter.export()

        client.get.assert_called_once_with("/risks")

    def test_export_writes_md_and_yaml_by_default(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = [_raw_risk_doc(1, "RISK-1")]

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RISK-1.md").exists()
        assert not (tmp_path / "risks" / "RISK-1.json").exists()
        assert (tmp_path / "risks" / "RISK-1.yaml").exists()

    def test_export_writes_json_with_keep_raw_json(self, tmp_path: Path) -> None:
        client = MagicMock()
        client.get.return_value = [_raw_risk_doc(1, "RISK-1")]

        RisksExporter(client, tmp_path / "risks", keep_raw_json=True).export()

        assert (tmp_path / "risks" / "RISK-1.json").exists()


class TestExporterProgress:
    @pytest.mark.parametrize(
        "exporter_cls, method_name, payload, text",
        [
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

        gov_cls.assert_called_once_with(
            client, tmp_path / "govs", force=False, keep_raw_json=False,
        )
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

        kwargs = {"force": False, "keep_raw_json": False}
        gov_cls.assert_called_once_with(client, tmp_path / "govs", **kwargs)
        pol_cls.assert_called_once_with(client, tmp_path / "pols", **kwargs)
        pro_cls.assert_called_once_with(client, tmp_path / "pros", **kwargs)
        risk_cls.assert_called_once_with(client, tmp_path / "risks", **kwargs)

        gov_instance.export.assert_called_once()
        pol_instance.export.assert_called_once()
        pro_instance.export.assert_called_once()
        risk_instance.export.assert_called_once()

    def test_force_and_keep_raw_json_passed_to_exporters(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        gov_cls = MagicMock(return_value=MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", gov_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.PoliciesExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", MagicMock())

        with patch("sys.argv", ["ctrlmap-cli", "--copy-gov", "--force", "--keep-raw-json"]):
            from ctrlmap_cli.cli import main
            main()

        gov_cls.assert_called_once_with(
            client, tmp_path / "govs", force=True, keep_raw_json=True,
        )

    def test_copy_pro_alias_uses_pros_output_dir(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        pro_instance = MagicMock()
        pro_cls = MagicMock(return_value=pro_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.PoliciesExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", pro_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", MagicMock())

        with patch("sys.argv", ["ctrlmap-cli", "--copy-pro"]):
            from ctrlmap_cli.cli import main
            main()

        pro_cls.assert_called_once_with(
            client, tmp_path / "pros", force=False, keep_raw_json=False,
        )
        pro_instance.export.assert_called_once()
