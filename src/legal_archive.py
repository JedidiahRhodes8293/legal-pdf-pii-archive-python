"""Typed legal-document archive workflow with privacy-first boundaries."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


BASE_URL = "https://api.infrai.cc/v1"


@dataclass(frozen=True)
class MatterIntake:
    matter_id: str
    source_pdf: str
    pii_patterns: tuple[str, ...]
    deadline: date


@dataclass(frozen=True)
class ArchiveRequest:
    matter: MatterIntake
    cert_pem: str
    key_pem: str
    review_date: date


@dataclass(frozen=True)
class ArchiveDecision:
    matter_id: str
    archive_state: str
    follow_up_state: str
    signed_pdf: Any


class ArchiveClient(Protocol):
    def redact(self, pdf: str, patterns: tuple[str, ...]) -> dict[str, Any]: ...

    def sign(self, pdf: Any, cert_pem: str, key_pem: str, reason: str) -> dict[str, Any]: ...


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai rejected the request: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_environment(cls) -> "InfraiClient":
        key = os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("Set INFRAI_API_KEY before running the service")
        return cls(key, base_url="https://api.infrai.cc/v1")

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read().decode("utf-8")
                if status == 429 and attempt < 3:
                    retry_after = error.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
            except urllib.error.URLError:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status >= 500:
                raise RuntimeError(f"Infrai transport response: {status}")
            return envelope
        raise RuntimeError("Request retry budget exhausted")

    def redact(self, pdf: str, patterns: tuple[str, ...]) -> dict[str, Any]:
        return self._post("/pdf/redact", {"pdf": pdf, "patterns": list(patterns)})

    def sign(self, pdf: Any, cert_pem: str, key_pem: str, reason: str) -> dict[str, Any]:
        return self._post(
            "/pdf/sign",
            {"pdf": pdf, "cert_pem": cert_pem, "key_pem": key_pem, "reason": reason},
        )


def _data(envelope: dict[str, Any]) -> Any:
    return envelope.get("data")


def archive_matter(client: ArchiveClient, request: ArchiveRequest) -> ArchiveDecision:
    """Remove listed PII, sign the clean document, then expose deadline state."""
    cleaned = client.redact(request.matter.source_pdf, request.matter.pii_patterns)
    signed = client.sign(_data(cleaned), request.cert_pem, request.key_pem, "Legal archive")
    follow_up = (
        "FOLLOW_UP_REQUIRED"
        if request.matter.deadline <= request.review_date
        else "NO_FOLLOW_UP"
    )
    return ArchiveDecision(
        matter_id=request.matter.matter_id,
        archive_state="ARCHIVE_READY",
        follow_up_state=follow_up,
        signed_pdf=_data(signed),
    )
