from datetime import date

from legal_archive import ArchiveRequest, InfraiClient, MatterIntake, archive_matter


SAMPLE_PDF = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n186\n%%EOF\n"


def main() -> None:
    request = ArchiveRequest(
        matter=MatterIntake(
            matter_id="MAT-104",
            source_pdf=SAMPLE_PDF,
            pii_patterns=("email", "phone", "medical_record_number"),
            deadline=date(2026, 10, 20),
        ),
        cert_pem="configured-certificate",
        key_pem="configured-private-key",
        review_date=date(2026, 10, 25),
    )
    decision = archive_matter(InfraiClient.from_environment(), request)
    print({"matter_id": decision.matter_id, "archive_state": decision.archive_state, "follow_up_state": decision.follow_up_state})


if __name__ == "__main__":
    main()
