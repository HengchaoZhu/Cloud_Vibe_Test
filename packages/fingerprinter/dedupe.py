from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any, Protocol


class DocumentClassification(StrEnum):
    EXACT_DUPLICATE = "exact_duplicate"
    SAME_URL_UPDATED = "same_url_updated"
    SYNDICATED_DUPLICATE = "syndicated_duplicate"
    NEAR_DUPLICATE = "near_duplicate"
    NEW_DOCUMENT = "new_document"


class ClaimClassification(StrEnum):
    NEW = "new"
    DUPLICATE = "duplicate"
    UPDATED = "updated"
    KNOWN = "known"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class DedupeConfig:
    """Thresholds and knobs for classification behavior."""

    # Max simhash Hamming distance to treat content as near-duplicate.
    near_duplicate_hamming_threshold: int = 3
    # Jaccard similarity at which two structured-field maps are considered equal.
    structured_similarity_duplicate_threshold: float = 0.98
    # Similarity threshold for "known" claims that are similar but not exact.
    structured_similarity_known_threshold: float = 0.85


class DocumentLike(Protocol):
    canonical_url: str
    url_fingerprint: str
    content_fingerprint: str
    simhash: str | None
    source_reliability: float


class ClaimLike(Protocol):
    claim_fingerprint: str
    structured_fields: dict[str, Any]
    event_date: date | None
    confidence: float


class FingerprinterRepository(Protocol):
    """Storage queries required by dedupe classification."""

    def find_by_url_fingerprint(self, url_fingerprint: str) -> DocumentLike | None:
        ...

    def find_by_content_fingerprint(self, content_fingerprint: str) -> DocumentLike | None:
        ...

    def find_near_duplicate_by_simhash(
        self, simhash: str, threshold: int
    ) -> list[DocumentLike]:
        ...

    def find_claim_by_fingerprint(self, claim_fingerprint: str) -> ClaimLike | None:
        ...


class DedupeService:
    def __init__(self, repo: FingerprinterRepository, config: DedupeConfig | None = None):
        self.repo = repo
        self.config = config or DedupeConfig()

    def classify_document(
        self,
        candidate: Any,
        fetched_doc: DocumentLike,
    ) -> DocumentClassification:
        """Classify fetched doc against repository state.

        Decision precedence:
        URL/content exact > same-url-updated > same-content-syndicated > simhash near duplicate > new.
        """
        url_hit = self.repo.find_by_url_fingerprint(fetched_doc.url_fingerprint)
        if url_hit and url_hit.content_fingerprint == fetched_doc.content_fingerprint:
            return DocumentClassification.EXACT_DUPLICATE

        if url_hit and url_hit.content_fingerprint != fetched_doc.content_fingerprint:
            return DocumentClassification.SAME_URL_UPDATED

        content_hit = self.repo.find_by_content_fingerprint(fetched_doc.content_fingerprint)
        if content_hit:
            return DocumentClassification.SYNDICATED_DUPLICATE

        if fetched_doc.simhash:
            near_hits = self.repo.find_near_duplicate_by_simhash(
                fetched_doc.simhash,
                threshold=self.config.near_duplicate_hamming_threshold,
            )
            if near_hits:
                return DocumentClassification.NEAR_DUPLICATE

        return DocumentClassification.NEW_DOCUMENT

    def classify_claim(self, claim: ClaimLike) -> ClaimClassification:
        """Classify claim by fingerprint and structured field similarity."""
        existing = self.repo.find_claim_by_fingerprint(claim.claim_fingerprint)
        if not existing:
            return ClaimClassification.NEW

        similarity = _structured_similarity(existing.structured_fields, claim.structured_fields)

        if similarity >= self.config.structured_similarity_duplicate_threshold:
            return ClaimClassification.DUPLICATE

        if _conflicts_with_existing(existing, claim):
            return ClaimClassification.CONFLICTING

        if _is_more_complete(claim.structured_fields, existing.structured_fields) or _is_newer(
            claim.event_date, existing.event_date
        ):
            return ClaimClassification.UPDATED

        if similarity >= self.config.structured_similarity_known_threshold:
            return ClaimClassification.KNOWN

        return ClaimClassification.CONFLICTING


def _structured_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    if not left and not right:
        return 1.0
    left_items = {(k, _norm_val(v)) for k, v in left.items()}
    right_items = {(k, _norm_val(v)) for k, v in right.items()}
    union = left_items | right_items
    if not union:
        return 1.0
    return len(left_items & right_items) / len(union)


def _is_more_complete(new_fields: dict[str, Any], old_fields: dict[str, Any]) -> bool:
    new_non_empty = sum(1 for v in new_fields.values() if _has_value(v))
    old_non_empty = sum(1 for v in old_fields.values() if _has_value(v))
    return new_non_empty > old_non_empty


def _is_newer(new_date: date | None, old_date: date | None) -> bool:
    if new_date is None or old_date is None:
        return False
    return new_date > old_date


def _conflicts_with_existing(existing: ClaimLike, incoming: ClaimLike) -> bool:
    common_keys = set(existing.structured_fields) & set(incoming.structured_fields)
    for key in common_keys:
        old_val = _norm_val(existing.structured_fields[key])
        new_val = _norm_val(incoming.structured_fields[key])
        if _has_value(old_val) and _has_value(new_val) and old_val != new_val:
            return True
    return False


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return False
    return True


def _norm_val(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return tuple(_norm_val(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _norm_val(v)) for k, v in value.items()))
    return value
