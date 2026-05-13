"""Shared API for URL/content/claim fingerprinting."""

from normalizer.core import (
    canonicalize_url,
    claim_fingerprint_input,
    content_fingerprint,
    content_hash,
    normalize_text,
    simhash_text,
    url_fingerprint,
)

__all__ = [
    "canonicalize_url",
    "normalize_text",
    "content_hash",
    "simhash_text",
    "url_fingerprint",
    "content_fingerprint",
    "claim_fingerprint_input",
]
