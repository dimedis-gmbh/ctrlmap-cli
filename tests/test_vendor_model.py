from __future__ import annotations

from ctrlmap_cli.models.vendors import (
    QuickAssessmentQuestion,
    VendorAttachment,
    VendorContact,
    VendorDocument,
    VendorLink,
    VendorRisk,
)


class TestVendorDataclasses:
    def test_attachment_instantiation(self) -> None:
        attachment = VendorAttachment(
            id=10,
            filename="contract.pdf",
            signed_url="https://example.com/contract.pdf",
            created="2026-02-17T00:00:00Z",
        )
        assert attachment.id == 10
        assert attachment.filename == "contract.pdf"

    def test_link_instantiation(self) -> None:
        link = VendorLink(id=3, name="SOC2", url="https://example.com/soc2")
        assert link.name == "SOC2"
        assert link.url.endswith("/soc2")

    def test_contact_instantiation(self) -> None:
        contact = VendorContact(id=7, name="Jane Doe", email="jane@example.com")
        assert contact.id == 7
        assert contact.email == "jane@example.com"

    def test_risk_instantiation(self) -> None:
        risk = VendorRisk(
            id=4,
            code="RSK-4",
            name="Data loss",
            owner="Owner Name",
            inherent_score=5,
            inherent_level="Medium",
            current_score=3,
            current_level="Low",
            target_score=1,
            target_level="Low",
        )
        assert risk.code == "RSK-4"
        assert risk.target_score == 1

    def test_quick_assessment_instantiation(self) -> None:
        question = QuickAssessmentQuestion(
            code="VQ-001",
            title="Stores PII?",
            answer="Yes",
            risk_level="High",
            group="Risk Profile",
        )
        assert question.answer == "Yes"
        assert question.risk_level == "High"

    def test_document_defaults_use_independent_lists(self) -> None:
        first = VendorDocument(
            id=1,
            code="VND-1",
            name="Vendor One",
            status="Active",
            vendor_type="Services Vendor",
            owner="Owner One",
            tier="Critical",
            tags=["critical"],
            risk_score=2.0,
            description="Desc",
        )
        second = VendorDocument(
            id=2,
            code="VND-2",
            name="Vendor Two",
            status="Active",
            vendor_type="Services Vendor",
            owner="Owner Two",
            tier="Critical",
            tags=["infra"],
            risk_score=1.0,
            description="Desc",
        )

        first.documents.append(
            VendorAttachment(
                id=1,
                filename="file.pdf",
                signed_url="https://example.com/file.pdf",
                created="2026-02-17T00:00:00Z",
            )
        )

        assert len(first.documents) == 1
        assert second.documents == []
