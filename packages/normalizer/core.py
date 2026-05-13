from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
    "icid",
}

_WHITESPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def canonicalize_url(url: str) -> str:
    """Canonicalize a URL for dedupe: normalized scheme/host, no fragments, sorted query."""
    if not url:
        return ""

    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"

    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    if len(path) > 1:
        path = path.rstrip("/")

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query_pairs.sort(key=lambda item: (item[0], item[1]))
    query = urlencode(query_pairs, doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_text(text: str) -> str:
    """Lowercase and collapse whitespace for deterministic hashing/fingerprinting."""
    if not text:
        return ""
    lowered = text.casefold()
    return _WHITESPACE_RE.sub(" ", lowered).strip()


def content_hash(text: str) -> str:
    """Stable SHA-256 hash of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def simhash_text(text: str) -> str:
    """Compute a 64-bit simhash over normalized token stream."""
    tokens = _WORD_RE.findall(normalize_text(text))
    if not tokens:
        return "0" * 16

    bits = [0] * 64
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], "big", signed=False)
        for i in range(64):
            bits[i] += 1 if (value >> i) & 1 else -1

    fingerprint = 0
    for i, weight in enumerate(bits):
        if weight >= 0:
            fingerprint |= 1 << i
    return f"{fingerprint:016x}"


def url_fingerprint(url: str) -> str:
    """Fingerprint of canonical URL."""
    return content_hash(canonicalize_url(url))


def content_fingerprint(text: str, title: str = "") -> str:
    """Fingerprint from normalized title + content."""
    return content_hash(f"{normalize_text(title)}\n{normalize_text(text)}")


def claim_fingerprint_input(
    entity_id: str | None,
    event_type: str,
    event_date: str | None,
    structured_fields: dict,
) -> str:
    """Canonical text input used when generating claim fingerprints."""
    normalized_items = sorted((str(k), normalize_text(str(v))) for k, v in structured_fields.items())
    fields_blob = "|".join(f"{k}={v}" for k, v in normalized_items)
    return "::".join(
        [
            normalize_text(entity_id or ""),
            normalize_text(event_type),
            normalize_text(event_date or ""),
            fields_blob,
        ]
    )
