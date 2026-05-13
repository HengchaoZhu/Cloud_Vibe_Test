from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.storage.models.schema import ClaimVersion, Document, DocumentVersion


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_url_fingerprint(self, url_fingerprint: str) -> Document | None:
        """Exact lookup used by URL dedupe service."""
        stmt = select(Document).where(Document.url_fingerprint == url_fingerprint)
        return self.session.scalar(stmt)

    def get_version_by_content_fingerprint(self, content_fingerprint: str) -> DocumentVersion | None:
        """Exact lookup used by content dedupe service."""
        stmt = select(DocumentVersion).where(
            DocumentVersion.content_fingerprint == content_fingerprint
        )
        return self.session.scalar(stmt)


class ClaimRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_version_by_claim_fingerprint(self, claim_fingerprint: str) -> ClaimVersion | None:
        """Exact lookup used by claim dedupe + merge service."""
        stmt = select(ClaimVersion).where(ClaimVersion.claim_fingerprint == claim_fingerprint)
        return self.session.scalar(stmt)

    def list_versions_for_merge(self, claim_fingerprints: list[str]) -> list[ClaimVersion]:
        """Batch exact lookup used by merge service before reconciliation."""
        if not claim_fingerprints:
            return []
        stmt = select(ClaimVersion).where(ClaimVersion.claim_fingerprint.in_(claim_fingerprints))
        return list(self.session.scalars(stmt).all())
