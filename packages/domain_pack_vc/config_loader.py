from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventTypeConfig(BaseModel):
    description: str
    weight: float = Field(ge=0.0, le=1.0)


class EventTaxonomyConfig(BaseModel):
    event_types: dict[str, EventTypeConfig]


class QueryTemplateConfig(BaseModel):
    enabled: bool = True
    source_class: str
    priority: int = Field(ge=0)
    freshness_days: int = Field(ge=0)
    max_results: int = Field(gt=0)
    expected_event_types: list[str]
    precision_template: str
    recall_template: str


class QueryTemplatesConfig(BaseModel):
    path_types: dict[str, QueryTemplateConfig]


class SourceTypeConfig(BaseModel):
    enabled: bool = True
    class_name: str = Field(alias="class")
    domains: list[str] = Field(default_factory=list)


class SourceRegistryConfig(BaseModel):
    source_types: dict[str, SourceTypeConfig]


class ReliabilityBounds(BaseModel):
    min: float = Field(ge=0.0, le=1.0)
    max: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "ReliabilityBounds":
        if self.min > self.max:
            raise ValueError("bounds.min must be <= bounds.max")
        return self


class ReliabilityRulesConfig(BaseModel):
    priors: dict[str, float]
    adjustments: dict[str, float] = Field(default_factory=dict)
    bounds: ReliabilityBounds

    @model_validator(mode="after")
    def validate_priors(self) -> "ReliabilityRulesConfig":
        for source_type, prior in self.priors.items():
            if prior < self.bounds.min or prior > self.bounds.max:
                raise ValueError(
                    f"prior for '{source_type}' must be within [{self.bounds.min}, {self.bounds.max}]"
                )
        return self


class DomainConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_taxonomy: EventTaxonomyConfig
    query_templates: QueryTemplatesConfig
    source_registry: SourceRegistryConfig
    reliability_rules: ReliabilityRulesConfig

    def get_query_template(self, path_type: str) -> QueryTemplateConfig:
        return self.query_templates.path_types[path_type]

    @property
    def enabled_path_types(self) -> list[str]:
        return [
            path_type
            for path_type, cfg in self.query_templates.path_types.items()
            if cfg.enabled
        ]

    @property
    def reliability_priors(self) -> dict[str, float]:
        return dict(self.reliability_rules.priors)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping at root of {path}")
    return data


def load_domain_config(config_root: str | Path = "configs") -> DomainConfig:
    root = Path(config_root)

    event_taxonomy = EventTaxonomyConfig.model_validate(
        _load_yaml(root / "event_taxonomy.yaml")
    )
    query_templates = QueryTemplatesConfig.model_validate(
        _load_yaml(root / "query_templates.yaml")
    )
    source_registry = SourceRegistryConfig.model_validate(
        _load_yaml(root / "source_registry.yaml")
    )
    reliability_rules = ReliabilityRulesConfig.model_validate(
        _load_yaml(root / "reliability_rules.yaml")
    )

    _validate_cross_refs(query_templates, event_taxonomy, source_registry, reliability_rules)

    return DomainConfig(
        event_taxonomy=event_taxonomy,
        query_templates=query_templates,
        source_registry=source_registry,
        reliability_rules=reliability_rules,
    )


def _validate_cross_refs(
    query_templates: QueryTemplatesConfig,
    event_taxonomy: EventTaxonomyConfig,
    source_registry: SourceRegistryConfig,
    reliability_rules: ReliabilityRulesConfig,
) -> None:
    known_event_types = set(event_taxonomy.event_types)
    for path_type, query_cfg in query_templates.path_types.items():
        unknown_events = set(query_cfg.expected_event_types) - known_event_types
        if unknown_events:
            raise ValueError(
                f"path type '{path_type}' references unknown event types: {sorted(unknown_events)}"
            )

    known_sources = set(source_registry.source_types)
    unknown_priors = set(reliability_rules.priors) - known_sources
    if unknown_priors:
        raise ValueError(
            f"reliability priors reference unknown source types: {sorted(unknown_priors)}"
        )
