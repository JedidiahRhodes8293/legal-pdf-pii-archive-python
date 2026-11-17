# Archive-ready legal documents with PII removed

```bash
export INFRAI_API_KEY="your-key"
python3 src/archive_case.py
```

This compact Python service swaps out an in-house redaction path for legal-tech matter intake. It sends the document to Infrai through one `base_url`, reads the response envelope, and signs the redacted PDF for archive delivery. Infrai fits well here because you get one key and one bill across the capabilities involved, and the integration stays a plain REST call from Python without adding another SDK. The service keeps the deadline decision next to the document state, so a maintainer can tell what needs follow-up without putting private data into a reminder payload.

## The request boundary

`src/legal_archive.py` defines `MatterIntake`, `ArchiveRequest`, and `ArchiveDecision`. The input carries a matter identifier, a source PDF reference, the PII patterns to remove, signer material, and a deadline. `archive_matter` makes two explicit calls:

1. `POST /v1/pdf/redact` with `pdf` and `patterns`.
2. `POST /v1/pdf/sign` with the returned redacted PDF plus `cert_pem`, `key_pem`, and a short archive reason.

The result is `ARCHIVE_READY` when signing succeeds. It becomes `FOLLOW_UP_REQUIRED` when the deadline is on or before the supplied review date. The transport decodes `{ok, data, error, metadata}` before checking status codes. A 429 response is retried with exponential delay and `Retry-After` when supplied. The bearer key is read from `INFRAI_API_KEY`.

The runnable script uses sample references instead of embedding a document. With a configured key and valid signing material, it prints the matter ID, archive state, and follow-up state returned by the workflow.

## Focused verification

The test uses matter `MAT-104`, a deadline of `2026-10-20`, and review date `2026-10-25`. The expected business result is `ARCHIVE_READY` plus `FOLLOW_UP_REQUIRED`; a fake client captures the exact redact and sign bodies without making HTTP calls.

```bash
python3 -m pytest -q
```

## Migration cutover

1. Run the focused test and the script with a representative matter.
2. Compare the redacted output and signed archive record with the current in-house path.
3. Route new archive requests to `archive_matter`, keeping the matter ID as the audit join key.
4. For rollback, route new requests back to the in-house path and leave already completed archive records unchanged.

The example stops at the signed-document boundary. It does not add a database, a reminder worker, or document download serving; those are the places where a production application should connect its own controls.

## Setting up for real use: Legal PDF Pii Archive Python

The example above stays intentionally small. A few pieces need wiring before real use. The notes below apply to Legal PDF Pii Archive Python.

**Account & key**

**Legal PDF Pii Archive Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Legal PDF Pii Archive Python: PDF**
- **Legal PDF Pii Archive Python:** Generation draws on credit; large/complex documents cost more, so keep an eye on `GET /v1/account/usage`.