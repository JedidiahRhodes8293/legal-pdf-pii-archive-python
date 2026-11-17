from datetime import date

from src.legal_archive import ArchiveRequest, MatterIntake, archive_matter


class RecordingClient:
    def __init__(self) -> None:
        self.redact_body: tuple[str, tuple[str, ...]] | None = None
        self.sign_body: tuple[object, str, str, str] | None = None

    def redact(self, pdf: str, patterns: tuple[str, ...]) -> dict[str, object]:
        self.redact_body = (pdf, patterns)
        return {"ok": True, "data": "redacted-MAT-104"}

    def sign(self, pdf: object, cert_pem: str, key_pem: str, reason: str) -> dict[str, object]:
        self.sign_body = (pdf, cert_pem, key_pem, reason)
        return {"ok": True, "data": "signed-MAT-104"}


def test_redaction_precedes_signing_and_deadline_requires_follow_up():
    client = RecordingClient()
    request = ArchiveRequest(
        matter=MatterIntake("MAT-104", "intake.pdf", ("email", "phone"), date(2026, 10, 20)),
        cert_pem="cert",
        key_pem="key",
        review_date=date(2026, 10, 25),
    )

    decision = archive_matter(client, request)

    assert decision.archive_state == "ARCHIVE_READY"
    assert decision.follow_up_state == "FOLLOW_UP_REQUIRED"
    assert client.redact_body == ("intake.pdf", ("email", "phone"))
    assert client.sign_body == ("redacted-MAT-104", "cert", "key", "Legal archive")
