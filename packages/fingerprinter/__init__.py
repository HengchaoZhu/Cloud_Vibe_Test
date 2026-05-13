from .dedupe import (
    ClaimClassification,
    DedupeConfig,
    DedupeService,
    DocumentClassification,
)




from .core import (
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
    "ClaimClassification",
    "DedupeConfig",
    "DedupeService",
    "DocumentClassification",
"""Fingerprinting helpers built on top of normalizer primitives."""
]
