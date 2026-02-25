from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.exporters.policies import PoliciesExporter
from ctrlmap_cli.exporters.procedures import ProceduresExporter
from ctrlmap_cli.exporters.risks import RisksExporter
from ctrlmap_cli.models.config import AppConfig


def _make_risk_detail(doc_id: int = 32, code: str = "RSK-1", name: str = "Risk") -> dict:
    return {
        "id": doc_id,
        "riskid": code,
        "name": f" {name} ",
        "description": "risk body",
        "state": "red",
        "status": {"name": "Open"},
        "userDTO": {"fullname": "Owner"},
        "systemLabels": [],
        "scoreDetailMap": {},
        "businessImpact": "",
        "existingControls": "",
        "residualTreatmentPlan": "",
        "controls": [],
        "actionItems": [],
        "threats": [],
        "vulnerabilities": [],
    }


class _Concrete(BaseExporter):
    """Minimal concrete subclass for testing BaseExporter."""
    def export(self) -> None:
        pass

    def export_single(self, item_code: str) -> None:
        pass


class TestBaseExporter:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseExporter(MagicMock(), Path("/tmp/test"))  # type: ignore[abstract]

    def test_ensure_output_dir_creates_directory(self, tmp_path: Path) -> None:
        exporter = _Concrete(MagicMock(), tmp_path / "nested" / "dir")
        exporter._ensure_output_dir()
        assert (tmp_path / "nested" / "dir").is_dir()

    def test_log_prints_to_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exporter = _Concrete(MagicMock(), tmp_path)
        exporter._log("hello world")
        assert "hello world" in capsys.readouterr().out


class TestParseItemCode:
    def test_full_code(self) -> None:
        assert BaseExporter._parse_item_code("GOV-1", "GOV") == ("GOV-1", 1)

    def test_numeric_only(self) -> None:
        assert BaseExporter._parse_item_code("5", "RSK") == ("RSK-5", 5)

    def test_case_insensitive(self) -> None:
        assert BaseExporter._parse_item_code("gov-3", "GOV") == ("GOV-3", 3)

    def test_whitespace_stripped(self) -> None:
        assert BaseExporter._parse_item_code("  POL-7  ", "POL") == ("POL-7", 7)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid item code"):
            BaseExporter._parse_item_code("INVALID", "GOV")

    def test_wrong_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid item code"):
            BaseExporter._parse_item_code("POL-1", "GOV")


class TestReadLocalFrontmatter:
    def test_reads_frontmatter_from_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "GOV-1.md").write_text(
            "---\nid: GOV-1\ntitle: First Doc\nstatus: Approved\n---\n\n# GOV-1\n"
        )
        (tmp_path / "GOV-2.md").write_text(
            "---\nid: GOV-2\ntitle: Second Doc\n---\n\n# GOV-2\n"
        )
        exporter = _Concrete(MagicMock(), tmp_path)
        result = exporter._read_local_frontmatter()
        assert "GOV-1" in result
        assert result["GOV-1"]["title"] == "First Doc"
        assert "GOV-2" in result
        assert result["GOV-2"]["title"] == "Second Doc"

    def test_excludes_index_md(self, tmp_path: Path) -> None:
        (tmp_path / "index.md").write_text("---\ngenerated: now\n---\n\n# Index\n")
        (tmp_path / "GOV-1.md").write_text("---\nid: GOV-1\n---\n\n# GOV-1\n")
        exporter = _Concrete(MagicMock(), tmp_path)
        result = exporter._read_local_frontmatter()
        assert "index" not in result
        assert "GOV-1" in result

    def test_empty_dir(self, tmp_path: Path) -> None:
        exporter = _Concrete(MagicMock(), tmp_path)
        assert exporter._read_local_frontmatter() == {}

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        exporter = _Concrete(MagicMock(), tmp_path / "nonexistent")
        assert exporter._read_local_frontmatter() == {}

    def test_skips_files_without_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "GOV-1.md").write_text("# No frontmatter here\n")
        exporter = _Concrete(MagicMock(), tmp_path)
        assert exporter._read_local_frontmatter() == {}


class TestBaseExporterOverwrite:
    def test_should_write_returns_true_for_new_file(self, tmp_path: Path) -> None:
        exporter = _Concrete(MagicMock(), tmp_path)
        assert exporter._should_write(tmp_path / "new-file.md") is True

    def test_should_write_returns_true_with_force(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.md"
        existing.write_text("content")

        exporter = _Concrete(MagicMock(), tmp_path, force=True)
        assert exporter._should_write(existing) is True

    def test_should_write_prompts_and_respects_no(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.md"
        existing.write_text("content")

        exporter = _Concrete(MagicMock(), tmp_path)
        with patch("builtins.input", return_value="n"):
            assert exporter._should_write(existing) is False

    def test_should_write_prompts_and_respects_yes(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.md"
        existing.write_text("content")

        exporter = _Concrete(MagicMock(), tmp_path)
        with patch("builtins.input", return_value="y"):
            assert exporter._should_write(existing) is True

    def test_should_write_all_sets_overwrite_all(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("a")
        f2.write_text("b")

        exporter = _Concrete(MagicMock(), tmp_path)
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
    """Basic smoke tests; see test_risks.py for comprehensive coverage."""

    @staticmethod
    def _setup_client(list_items: list, details: dict) -> MagicMock:
        client = MagicMock()
        client.list_risks.return_value = {"riskDTOS": list_items}
        client.get_risk.side_effect = lambda rid: details.get(rid, {})
        client.get_risk_areas.return_value = []
        return client

    def test_export_calls_expected_endpoint(self, tmp_path: Path) -> None:
        client = self._setup_client(list_items=[], details={})

        RisksExporter(client, tmp_path / "risks").export()

        client.list_risks.assert_called_once()

    def test_export_writes_md_only_by_default(self, tmp_path: Path) -> None:
        detail = _make_risk_detail(32, "RSK-1")
        client = self._setup_client([{"id": 32}], {32: detail})

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()
        assert not (tmp_path / "risks" / "RSK-1.json").exists()
        assert not list((tmp_path / "risks").glob("*.yaml"))

    def test_export_writes_json_with_keep_raw_json(self, tmp_path: Path) -> None:
        detail = _make_risk_detail(32, "RSK-1")
        client = self._setup_client([{"id": 32}], {32: detail})

        RisksExporter(client, tmp_path / "risks", keep_raw_json=True).export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()
        assert (tmp_path / "risks" / "RSK-1.json").exists()


class TestExporterProgress:
    def test_risks_progress_log(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        detail = _make_risk_detail(32, "RSK-1")
        client = MagicMock()
        client.list_risks.return_value = {"riskDTOS": [{"id": 32}]}
        client.get_risk.return_value = detail
        client.get_risk_areas.return_value = []

        exporter = RisksExporter(client, tmp_path / "out")
        exporter.export()

        out = capsys.readouterr().out
        assert "Exporting risks" in out
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

    def test_copy_govs_uses_governance_output_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        gov_instance = MagicMock()
        gov_cls = MagicMock(return_value=gov_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", gov_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.PoliciesExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", MagicMock())
        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", MagicMock())

        with patch("sys.argv", ["ctrlmap-cli", "--copy-govs"]):
            from ctrlmap_cli.cli import main
            main()

        gov_cls.assert_called_once_with(
            client, tmp_path / "govs", force=False, keep_raw_json=False,
        )
        gov_instance.export.assert_called_once()

    def test_copy_gov_single_calls_export_single(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        gov_instance = MagicMock()
        gov_cls = MagicMock(return_value=gov_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", gov_cls)

        with patch("sys.argv", ["ctrlmap-cli", "--copy-gov", "GOV-1"]):
            from ctrlmap_cli.cli import main
            main()

        gov_cls.assert_called_once_with(
            client, tmp_path / "govs", force=False, keep_raw_json=False,
        )
        gov_instance.export_single.assert_called_once_with("GOV-1")

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
        vendor_instance = MagicMock()

        gov_cls = MagicMock(return_value=gov_instance)
        pol_cls = MagicMock(return_value=pol_instance)
        pro_cls = MagicMock(return_value=pro_instance)
        risk_cls = MagicMock(return_value=risk_instance)
        vendor_cls = MagicMock(return_value=vendor_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.GovernanceExporter", gov_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.PoliciesExporter", pol_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", pro_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", risk_cls)
        monkeypatch.setattr("ctrlmap_cli.cli.VendorsExporter", vendor_cls)

        with patch("sys.argv", ["ctrlmap-cli", "--copy-all"]):
            from ctrlmap_cli.cli import main
            main()

        kwargs = {"force": False, "keep_raw_json": False}
        gov_cls.assert_called_once_with(client, tmp_path / "govs", **kwargs)
        pol_cls.assert_called_once_with(client, tmp_path / "pols", **kwargs)
        pro_cls.assert_called_once_with(client, tmp_path / "pros", **kwargs)
        risk_cls.assert_called_once_with(client, tmp_path / "risks", **kwargs)
        vendor_cls.assert_called_once_with(client, tmp_path / "vendors", **kwargs)

        gov_instance.export.assert_called_once()
        pol_instance.export.assert_called_once()
        pro_instance.export.assert_called_once()
        risk_instance.export.assert_called_once()
        vendor_instance.export.assert_called_once()

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

        with patch("sys.argv", ["ctrlmap-cli", "--copy-govs", "--force", "--keep-raw-json"]):
            from ctrlmap_cli.cli import main
            main()

        gov_cls.assert_called_once_with(
            client, tmp_path / "govs", force=True, keep_raw_json=True,
        )

    def test_copy_pro_singular_calls_export_single(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        pro_instance = MagicMock()
        pro_cls = MagicMock(return_value=pro_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.ProceduresExporter", pro_cls)

        with patch("sys.argv", ["ctrlmap-cli", "--copy-pro", "PRO-3"]):
            from ctrlmap_cli.cli import main
            main()

        pro_cls.assert_called_once_with(
            client, tmp_path / "pros", force=False, keep_raw_json=False,
        )
        pro_instance.export_single.assert_called_once_with("PRO-3")

    def test_copy_risk_singular_calls_export_single(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        risk_instance = MagicMock()
        risk_cls = MagicMock(return_value=risk_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.RisksExporter", risk_cls)

        with patch("sys.argv", ["ctrlmap-cli", "--copy-risk", "RSK-5"]):
            from ctrlmap_cli.cli import main
            main()

        risk_cls.assert_called_once_with(
            client, tmp_path / "risks", force=False, keep_raw_json=False,
        )
        risk_instance.export_single.assert_called_once_with("RSK-5")

    def test_copy_vendor_singular_calls_export_single(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        client = self._setup_cli(monkeypatch, tmp_path)
        vendor_instance = MagicMock()
        vendor_cls = MagicMock(return_value=vendor_instance)

        monkeypatch.setattr("ctrlmap_cli.cli.VendorsExporter", vendor_cls)

        with patch("sys.argv", ["ctrlmap-cli", "--copy-vendor", "VND-17"]):
            from ctrlmap_cli.cli import main
            main()

        vendor_cls.assert_called_once_with(
            client, tmp_path / "vendors", force=False, keep_raw_json=False,
        )
        vendor_instance.export_single.assert_called_once_with("VND-17")
