from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TaskType = Literal["daily_monitor", "historical_query", "deep_dive"]
PrivacyMode = Literal["public_only", "internal_allowed"]

PathType = Literal[
    "entity_identity",
    "official_source",
    "funding_deal",
    "product_traction",
    "people_hiring",
    "customer_partner",
    "market_competition",
    "risk_regulatory",
    "financial_public",
    "technical_signal",
]

SourceClass = Literal["web", "news", "company_site", "database", "filing", "social_allowed"]

EventType = Literal[
    "funding",
    "mna",
    "product_launch",
    "partnership",
    "customer_win",
    "hiring",
    "layoff",
    "executive_change",
    "regulatory",
    "lawsuit",
    "security_incident",
    "financial_metric",
    "market_signal",
    "technical_signal",
    "other",
]

EvidenceSourceType = Literal["official", "news", "database", "filing", "blog", "social_allowed", "other"]
EvidenceStance = Literal["support", "refute", "context"]
NoveltyStatus = Literal["new", "known", "updated", "duplicate", "conflicting"]
ImpactLabel = Literal["opportunity", "risk", "neutral", "unknown"]


class MonitorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    user_query: str
    targets: list[str] = Field(default_factory=list)
    domain: str = "vc_company_monitor"
    task_type: TaskType
    time_window: dict[str, str]
    languages: list[str] = Field(default_factory=lambda: ["en"])
    geography: list[str] = Field(default_factory=list)
    source_constraints: dict[str, Any] = Field(default_factory=dict)
    privacy_mode: PrivacyMode = "public_only"


class SearchTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    path_type: PathType
    query: str
    source_class: SourceClass
    priority: int
    freshness_days: int
    expected_event_types: list[EventType]
    inclusion_domains: list[str] = Field(default_factory=list)
    exclusion_domains: list[str] = Field(default_factory=list)
    max_results: int = 20


class SearchCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    adapter_name: str
    title: str | None = None
    url: str
    snippet: str | None = None
    source_name: str | None = None
    published_at: datetime | None = None
    rank: int
    raw_response: dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    canonical_url: str
    original_url: str
    title: str | None = None
    source_domain: str
    source_name: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    author: str | None = None
    language: str | None = None
    raw_text: str
    normalized_text: str
    url_fingerprint: str
    content_fingerprint: str
    simhash: str | None = None
    source_reliability: float


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    doc_id: str
    claim_id: str | None = None
    quote_or_span: str
    claim_text: str
    source_type: EvidenceSourceType
    evidence_date: date | None = None
    relevance: float
    reliability: float
    stance: EvidenceStance


class CompanyClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    canonical_entity_id: str | None = None
    company_name: str
    event_type: EventType
    event_date: date | None = None
    normalized_claim: str
    structured_fields: dict[str, Any] = Field(default_factory=dict)
    claim_fingerprint: str
    novelty_status: NoveltyStatus
    confidence: float
    importance_score: float
    vc_impact: ImpactLabel


class DailyDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    digest_id: str
    digest_date: date
    title: str
    summary: str
    top_claim_ids: list[str] = Field(default_factory=list)
    total_claims: int = 0
    generated_at: datetime


class RunMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    num_search_tasks: int = 0
    num_candidates: int = 0
    num_documents_fetched: int = 0
    num_exact_duplicates: int = 0
    num_near_duplicates: int = 0
    num_new_claims: int = 0
    num_updated_claims: int = 0
    num_conflicting_claims: int = 0
    ai_extraction_cost: float = 0.0
    time_to_digest_seconds: float = 0.0
    user_feedback_useful_rate: float = 0.0
