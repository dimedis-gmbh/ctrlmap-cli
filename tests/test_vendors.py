from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from ctrlmap_cli.exporters.vendors import (
    VendorsExporter, _as_float, _as_int, _looks_like_markdown, _slugify,
)


def _make_score(
    score: int = 5,
    score_name: str = "Mittel",
    likelihood: int = 1,
    likelihood_label: str = "Selten",
    impact: int = 5,
    impact_label: str = "Katastrophal",
) -> Dict[str, Any]:
    return {
        "score": score,
        "scoreName": score_name,
        "likelihood": likelihood,
        "likelihoodLabel": likelihood_label,
        "impact": impact,
        "impactLabel": impact_label,
    }


def _make_vendor_risk(
    risk_id: int = 33,
    riskid: str = "RSK-2",
    name: str = "Ransomware",
    owner: str = "Patrick Apolinarski",
) -> Dict[str, Any]:
    return {
        "id": risk_id,
        "riskid": riskid,
        "name": name,
        "userDTO": {"fullname": owner},
        "scoreDetailMap": {
            "inherent": _make_score(20, "Schwerwiegend", 5, "Bestimmt", 4, "Schwerwiegend"),
            "current": _make_score(5, "Mittel", 1, "Selten", 5, "Katastrophal"),
            "target": _make_score(1, "Niedrig", 1, "Selten", 1, "Unbedeutend"),
        },
        "deleted": False,
    }


def _make_hyperlink(
    link_id: int = 56,
    name: str = "ISO 27001",
    url: str = "https://example.com/cert.pdf",
) -> Dict[str, Any]:
    return {"id": link_id, "name": name, "hyperLink": url, "vendorId": 41}


def _make_quick_assessment() -> Dict[str, Any]:
    return {
        "totalQuestions": 2,
        "answeredQuestions": 2,
        "category": "Quick Assessment",
        "vendorQuestionAnswerDTOList": [
            {
                "id": 242,
                "code": "VQ-001",
                "title": "Does the vendor store PII?",
                "groupName": "Risk Profile",
                "selectedAnswerId": 1,
                "answerWeightage": 3,
                "answersList": [
                    {"id": 1, "answer": "Yes", "order": 1, "weightage": 3},
                    {"id": 2, "answer": "No", "order": 2, "weightage": 1},
                ],
            },
            {
                "id": 243,
                "code": "VQ-002",
                "title": "Contract with confidentiality clause?",
                "groupName": "Risk Profile",
                "selectedAnswerId": 8,
                "answerWeightage": 1,
                "answersList": [
                    {"id": 7, "answer": "No", "order": 2, "weightage": 3},
                    {"id": 8, "answer": "Yes", "order": 1, "weightage": 1},
                ],
            },
        ],
    }


def _make_detail(
    vendor_id: int = 41,
    code: str = "VND-17",
    name: str = "Hetzner",
    description: str = "Test vendor description.",
    status: str = "Active",
    vendor_type: str = "Services Vendor",
    owner: str = "Thorsten Kramm",
    tier: str = "Geschäftskritisch",
    risk_score: float = 2.0,
    documents: Optional[List[Dict[str, Any]]] = None,
    assessment_id: int = 42,
    link_id: int = 42,
) -> Dict[str, Any]:
    return {
        "id": vendor_id,
        "code": code,
        "vendorName": name,
        "vendorStatus": {"id": 30, "name": status},
        "vendorType": {"id": 1, "name": vendor_type},
        "internalContact": {"fullname": owner},
        "vendorTier": {"id": 1, "name": tier},
        "tags": [{"name": "critical"}, {"displayName": "infra"}],
        "avgRiskScore": risk_score,
        "description": description,
        "documentDTOSet": documents or [],
        "vendorQuickAssessmentId": assessment_id,
        "currentAssessmentLinkId": link_id,
        "actionItems": [{"evidenceCode": "AI-10", "title": "Review contract"}],
    }


def _make_detail_with_docs() -> Dict[str, Any]:
    return _make_detail(documents=[
        {
            "id": 15,
            "filename": "dpa-audit.pdf",
            "signedURL": "https://s3.example.com/dpa-audit.pdf",
            "createdate": "2025-07-29T11:02:05.000+00:00",
        },
        {
            "id": 30,
            "filename": "certificate.pdf",
            "signedURL": "https://s3.example.com/certificate.pdf",
            "createdate": "2025-12-05T14:01:29.000+00:00",
        },
    ])


def _setup_client(
    list_response: Any = None,
    detail: Optional[Dict[str, Any]] = None,
    risks: Optional[List[Dict[str, Any]]] = None,
    hyperlinks: Optional[List[Dict[str, Any]]] = None,
    contacts: Optional[List[Dict[str, Any]]] = None,
    quick_assessment: Optional[Dict[str, Any]] = None,
) -> MagicMock:
    client = MagicMock()
    client.list_vendors.return_value = list_response if list_response is not None else []
    client.get_vendor.return_value = detail or {}
    client.get_vendor_risks.return_value = risks or []
    client.get_vendor_hyperlinks.return_value = hyperlinks or []
    client.get_vendor_contacts.return_value = contacts or []
    client.get_vendor_quick_assessment.return_value = quick_assessment or {}
    client.download_file.return_value = b"fake file content"
    return client


class TestVendorsExporterEndpoints:
    def test_list_call(self, tmp_path: Path) -> None:
        client = _setup_client()
        VendorsExporter(client, tmp_path / "vendors").export()
        client.list_vendors.assert_called_once()

    def test_fetches_detail_per_vendor(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=_make_quick_assessment(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        client.get_vendor.assert_called_once_with(41)
        client.get_vendor_risks.assert_called_once_with(41)
        client.get_vendor_hyperlinks.assert_called_once_with(41)
        client.get_vendor_contacts.assert_called_once_with(41)

    def test_empty_list_creates_index_only(self, tmp_path: Path) -> None:
        client = _setup_client()
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "index.md").exists()
        assert not list((tmp_path / "vendors").glob("VND-*.md"))

    def test_skips_vendor_without_id(self, tmp_path: Path) -> None:
        client = _setup_client(list_response=[{"id": 0}])
        VendorsExporter(client, tmp_path / "vendors").export()
        client.get_vendor.assert_not_called()


class TestVendorsExporterOutput:
    def test_creates_md_file(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=_make_quick_assessment(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_no_json_by_default(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=_make_quick_assessment(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert not (tmp_path / "vendors" / "VND-17.json").exists()

    def test_keep_raw_json(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=_make_quick_assessment(),
        )
        VendorsExporter(client, tmp_path / "vendors", keep_raw_json=True).export()
        assert (tmp_path / "vendors" / "VND-17.json").exists()


class TestVendorsFrontmatter:
    def _get_frontmatter(self, tmp_path: Path) -> str:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=_make_quick_assessment(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        # Extract frontmatter between --- markers
        parts = content.split("---")
        return parts[1] if len(parts) >= 3 else ""

    def test_frontmatter_has_id(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "id: VND-17" in fm

    def test_frontmatter_has_title(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "title: Hetzner" in fm

    def test_frontmatter_has_status(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "status: Active" in fm

    def test_frontmatter_has_vendor_type(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "vendor_type: Services Vendor" in fm

    def test_frontmatter_has_owner(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "owner: Thorsten Kramm" in fm

    def test_frontmatter_has_risk_score(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "risk_score: 2.0" in fm

    def test_frontmatter_has_tags(self, tmp_path: Path) -> None:
        fm = self._get_frontmatter(tmp_path)
        assert "- critical" in fm
        assert "- infra" in fm


class TestVendorsMarkdownContent:
    def _get_content(
        self,
        tmp_path: Path,
        detail: Optional[Dict[str, Any]] = None,
        risks: Optional[List[Dict[str, Any]]] = None,
        hyperlinks: Optional[List[Dict[str, Any]]] = None,
        quick_assessment: Optional[Dict[str, Any]] = None,
    ) -> str:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail or _make_detail(),
            risks=risks,
            hyperlinks=hyperlinks,
            quick_assessment=quick_assessment,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        return (tmp_path / "vendors" / "VND-17.md").read_text()

    def test_documents_links_section(self, tmp_path: Path) -> None:
        content = self._get_content(tmp_path)
        assert "## Documents & Links" in content

    def test_quick_assessment_section(self, tmp_path: Path) -> None:
        content = self._get_content(
            tmp_path, quick_assessment=_make_quick_assessment(),
        )
        assert "## Quick Assessment" in content
        assert "VQ-001" in content
        assert "**Yes**" in content

    def test_risks_section(self, tmp_path: Path) -> None:
        content = self._get_content(
            tmp_path, risks=[_make_vendor_risk()],
        )
        assert "### Risks" in content
        assert "RSK-2" in content
        assert "Ransomware" in content

    def test_action_items_section(self, tmp_path: Path) -> None:
        content = self._get_content(tmp_path)
        assert "### Action Items" in content
        assert "AI-10" in content

    def test_hyperlinks_displayed(self, tmp_path: Path) -> None:
        content = self._get_content(
            tmp_path, hyperlinks=[_make_hyperlink()],
        )
        assert "### Links" in content
        assert "[ISO 27001](https://example.com/cert.pdf)" in content

    def test_empty_risks(self, tmp_path: Path) -> None:
        content = self._get_content(tmp_path, risks=[])
        assert "No risks" in content

    def test_empty_hyperlinks(self, tmp_path: Path) -> None:
        content = self._get_content(tmp_path, hyperlinks=[])
        assert "No links" in content

    def test_empty_quick_assessment(self, tmp_path: Path) -> None:
        content = self._get_content(tmp_path, quick_assessment=None)
        assert "No quick assessment data" in content


class TestMarkdownDetection:
    def test_heading(self) -> None:
        assert _looks_like_markdown("# Heading")

    def test_subheading(self) -> None:
        assert _looks_like_markdown("## Subheading")

    def test_bold(self) -> None:
        assert _looks_like_markdown("Some **bold** text")

    def test_unordered_list(self) -> None:
        assert _looks_like_markdown("- item one\n- item two")

    def test_ordered_list(self) -> None:
        assert _looks_like_markdown("1. first\n2. second")

    def test_link(self) -> None:
        assert _looks_like_markdown("[click](https://example.com)")

    def test_code_fence(self) -> None:
        assert _looks_like_markdown("```python\ncode\n```")

    def test_blockquote(self) -> None:
        assert _looks_like_markdown("> quote text")

    def test_plain_text(self) -> None:
        assert not _looks_like_markdown("Just a normal sentence.")

    def test_plain_multiline(self) -> None:
        assert not _looks_like_markdown(
            "pqina, Pintura Image Editor\nDie Software wird eingebettet."
        )

    def test_markdown_wraps_in_code_fence(self, tmp_path: Path) -> None:
        md_desc = "# Title\n\n## Section\n\nSome **bold** text."
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(description=md_desc),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "```markdown" in content
        assert "# Title" in content

    def test_plain_text_no_fence(self, tmp_path: Path) -> None:
        plain = "Simple vendor description."
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(description=plain),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "```markdown" not in content
        assert "Simple vendor description." in content


class TestSlugify:
    def test_simple(self) -> None:
        assert _slugify("Hetzner") == "hetzner"

    def test_spaces(self) -> None:
        assert _slugify("HRlab GmbH") == "hrlab-gmbh"

    def test_special_chars(self) -> None:
        assert _slugify("99sensors GmbH Germany") == "99sensors-gmbh-germany"

    def test_trailing_special(self) -> None:
        assert _slugify("NETZATELIER Dr. Burkhard Apsner") == "netzatelier-dr-burkhard-apsner"


class TestDocumentDownloads:
    def test_downloads_files(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail_with_docs(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()

        doc_dir = tmp_path / "vendors" / "documents" / "VND-17-hetzner"
        assert doc_dir.exists()
        assert (doc_dir / "dpa-audit.pdf").exists()
        assert (doc_dir / "certificate.pdf").exists()
        assert (doc_dir / "dpa-audit.pdf").read_bytes() == b"fake file content"

    def test_no_downloads_when_no_docs(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        docs_dir = tmp_path / "vendors" / "documents"
        assert not docs_dir.exists()

    def test_download_failure_logs_warning(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail_with_docs(),
        )
        client.download_file.side_effect = Exception("download failed")
        VendorsExporter(client, tmp_path / "vendors").export()

        captured = capsys.readouterr()
        assert "Warning: failed to download" in captured.out

    def test_md_references_downloaded_files(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail_with_docs(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "documents/VND-17-hetzner/dpa-audit.pdf" in content

    def test_sanitizes_attachment_filename_and_blocks_traversal(self, tmp_path: Path) -> None:
        traversal_name = "../../../outside-target.txt"
        detail = _make_detail(documents=[
            {
                "id": 15,
                "filename": traversal_name,
                "signedURL": "https://s3.example.com/outside-target.txt",
                "createdate": "2025-07-29T11:02:05.000+00:00",
            },
        ])
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )

        VendorsExporter(client, tmp_path / "vendors").export()

        safe_target = tmp_path / "vendors" / "documents" / "VND-17-hetzner" / "outside-target.txt"
        escaped_target = tmp_path / "vendors" / "outside-target.txt"

        assert safe_target.exists()
        assert not escaped_target.exists()


class TestVendorsIndex:
    def _export_and_read_index(
        self, tmp_path: Path, vendors: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        if vendors is None:
            vendors = [{"id": 41}]
        client = _setup_client(
            list_response=vendors,
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        return (tmp_path / "vendors" / "index.md").read_text()

    def test_index_created(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path)
        assert content

    def test_index_has_frontmatter(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path)
        assert "generated:" in content
        assert "document_count:" in content

    def test_index_lists_vendor(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path)
        assert "[VND-17](VND-17.md)" in content
        assert "Hetzner" in content

    def test_index_metadata_bullets(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path)
        assert "**Status:** Active" in content
        assert "**Vendor Type:** Services Vendor" in content
        assert "**Risk Score:**" in content
        assert "**Tier:**" in content

    def test_index_summary_line(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path)
        assert "1 vendor exported on" in content

    def test_index_singular_noun(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path, vendors=[{"id": 41}])
        assert "1 vendor " in content

    def test_empty_index(self, tmp_path: Path) -> None:
        content = self._export_and_read_index(tmp_path, vendors=[])
        assert "0 vendors exported on" in content

    def test_index_falls_back_to_file_stem_when_code_missing(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(code=""),
        )
        VendorsExporter(client, tmp_path / "vendors").export()

        content = (tmp_path / "vendors" / "index.md").read_text()
        assert "## [VND-41](VND-41.md)" in content


class TestVendorsLineLength:
    def test_vendor_and_index_markdown_lines_stay_within_limit(self, tmp_path: Path) -> None:
        long_name = (
            "Vendor Name That Is Unexpectedly Extremely Long To Stress Index Heading Length "
            "And Verify Wrapping Behavior"
        )
        long_filename = (
            "this-is-a-very-long-filename-that-can-easily-exceed-the-usual-markdown-line-limit-"
            "when-combined-with-a-long-directory-name.pdf"
        )
        long_url = "https://example.com/" + ("path/" * 40) + "certificate.pdf"
        long_risk = _make_vendor_risk(
            name=(
                "A very long risk title that makes this line extremely long and likely over the configured "
                "markdown line length threshold"
            )
        )

        detail = _make_detail(
            name=long_name,
            documents=[{
                "id": 15,
                "filename": long_filename,
                "signedURL": "https://s3.example.com/long.pdf",
                "createdate": "2025-07-29T11:02:05.000+00:00",
            }],
        )
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
            risks=[long_risk],
            hyperlinks=[_make_hyperlink(url=long_url)],
            quick_assessment=_make_quick_assessment(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()

        for path in (
            tmp_path / "vendors" / "VND-17.md",
            tmp_path / "vendors" / "index.md",
        ):
            content = path.read_text()
            assert max(len(line) for line in content.splitlines()) <= 120


class TestVendorsProgress:
    def test_progress_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        captured = capsys.readouterr()
        assert "Exporting vendors..." in captured.out
        assert "VND-17" in captured.out
        assert "1 documents" in captured.out

    def test_empty_progress(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client()
        VendorsExporter(client, tmp_path / "vendors").export()
        captured = capsys.readouterr()
        assert "0 documents" in captured.out


class TestVendorsOverwrite:
    def test_force_overwrites(self, tmp_path: Path) -> None:
        out = tmp_path / "vendors"
        out.mkdir()
        (out / "VND-17.md").write_text("old")
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
        )
        VendorsExporter(client, out, force=True).export()
        assert "old" not in (out / "VND-17.md").read_text()

    def test_prompt_no_skips(self, tmp_path: Path) -> None:
        out = tmp_path / "vendors"
        out.mkdir()
        (out / "VND-17.md").write_text("old")
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
        )
        with patch("builtins.input", return_value="no"):
            VendorsExporter(client, out).export()
        assert (out / "VND-17.md").read_text() == "old"

    def test_new_files_no_prompt(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()


class TestVendorsEdgeCases:
    def test_missing_owner(self, tmp_path: Path) -> None:
        detail = _make_detail()
        del detail["internalContact"]
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_missing_status(self, tmp_path: Path) -> None:
        detail = _make_detail()
        del detail["vendorStatus"]
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_missing_tier(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["vendorTier"] = None
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_tags_as_strings(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["tags"] = ["tag-a", "tag-b"]
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "tag-a" in content

    def test_empty_description(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(description=""),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "No notes or descriptions" in content

    def test_no_assessment_ids(self, tmp_path: Path) -> None:
        detail = _make_detail()
        del detail["vendorQuickAssessmentId"]
        del detail["currentAssessmentLinkId"]
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        client.get_vendor_quick_assessment.assert_not_called()

    def test_invalid_assessment_ids_do_not_trigger_call(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["vendorQuickAssessmentId"] = ""
        detail["currentAssessmentLinkId"] = "not-a-number"
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        client.get_vendor_quick_assessment.assert_not_called()

    def test_dict_wrapped_vendor_list(self, tmp_path: Path) -> None:
        """API may wrap vendor list in a dict with vendorDTOS key."""
        client = _setup_client(
            list_response={"vendorDTOS": [{"id": 41}]},
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_dict_wrapped_vendors_key(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"vendors": [{"id": 41}]},
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_dict_wrapped_content_key(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"content": [{"id": 41}]},
            detail=_make_detail(),
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_list_attachments(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["documentDTOSet"] = "not a list"
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_dict_items_in_attachments(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["documentDTOSet"] = ["not a dict", 42]
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_list_hyperlinks(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            hyperlinks="not a list",  # type: ignore[arg-type]
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_dict_items_in_hyperlinks(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            hyperlinks=["not a dict"],  # type: ignore[list-item]
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_list_contacts(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            contacts="not a list",  # type: ignore[arg-type]
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_dict_items_in_contacts(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            contacts=["not a dict", 99],  # type: ignore[list-item]
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_list_risks(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            risks="not a list",  # type: ignore[arg-type]
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_non_dict_items_in_risks(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            risks=["not a dict"],  # type: ignore[list-item]
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_score_detail_map_not_dict(self, tmp_path: Path) -> None:
        risk_raw = _make_vendor_risk()
        risk_raw["scoreDetailMap"] = "not a dict"
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            risks=[risk_raw],
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        assert (tmp_path / "vendors" / "VND-17.md").exists()

    def test_quick_assessment_non_list_questions(self, tmp_path: Path) -> None:
        qa = {"vendorQuestionAnswerDTOList": "not a list"}
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=qa,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "No quick assessment data" in content

    def test_quick_assessment_non_dict_question(self, tmp_path: Path) -> None:
        qa = {"vendorQuestionAnswerDTOList": ["not a dict", 42]}
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=_make_detail(),
            quick_assessment=qa,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "No quick assessment data" in content

    def test_download_skips_missing_url(self, tmp_path: Path) -> None:
        detail = _make_detail(documents=[
            {"id": 15, "filename": "file.pdf", "signedURL": "", "createdate": ""},
        ])
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        client.download_file.assert_not_called()

    def test_download_skips_missing_filename(self, tmp_path: Path) -> None:
        detail = _make_detail(documents=[
            {"id": 15, "filename": "", "signedURL": "https://s3.example.com/f", "createdate": ""},
        ])
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        client.download_file.assert_not_called()

    def test_no_action_items_in_output(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["actionItems"] = []
        client = _setup_client(
            list_response=[{"id": 41}],
            detail=detail,
        )
        VendorsExporter(client, tmp_path / "vendors").export()
        content = (tmp_path / "vendors" / "VND-17.md").read_text()
        assert "No action items" in content


class TestAsIntAsFloat:
    def test_as_int_from_string(self) -> None:
        assert _as_int("42") == 42

    def test_as_int_from_invalid_string(self) -> None:
        assert _as_int("abc") == 0

    def test_as_int_from_none(self) -> None:
        assert _as_int(None) == 0

    def test_as_float_from_string(self) -> None:
        assert _as_float("3.14") == 3.14

    def test_as_float_from_invalid_string(self) -> None:
        assert _as_float("abc") == 0.0

    def test_as_float_from_none(self) -> None:
        assert _as_float(None) == 0.0
