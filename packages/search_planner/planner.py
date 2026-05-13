from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
from typing import Any

PATH_CONFIG: dict[str, dict[str, Any]] = {
    "entity_identity": {
        "source_class": "web",
        "priority": 100,
        "freshness_days": 30,
        "max_results": 10,
        "expected_event_types": ["identity", "official_domain"],
        "precision_pattern": '"{target}" (founder OR headquarters OR "official site")',
        "recall_pattern": '{target} company profile',
    },
    "official_source": {
        "source_class": "company_site",
        "priority": 95,
        "freshness_days": 14,
        "max_results": 20,
        "expected_event_types": ["announcement", "product_launch"],
        "precision_pattern": 'site:{domain} ("{target}" OR blog OR press OR announcement)',
        "recall_pattern": '{target} blog press release announcement',
    },
    "funding_deal": {
        "source_class": "news",
        "priority": 90,
        "freshness_days": 30,
        "max_results": 25,
        "expected_event_types": ["funding", "mna"],
        "precision_pattern": '"{target}" (raised OR funding OR "Series A" OR acquisition OR acquired)',
        "recall_pattern": '{target} investors valuation deal round',
    },
    "product_traction": {
        "source_class": "news",
        "priority": 85,
        "freshness_days": 21,
        "max_results": 20,
        "expected_event_types": ["product_launch", "customer_win", "market_signal"],
        "precision_pattern": '"{target}" (launch OR product OR customer OR "case study")',
        "recall_pattern": '{target} adoption users growth partnership',
    },
}

DEFAULTS = {
    "priority": 50,
    "freshness_days": 30,
    "max_results": 20,
}


@dataclass(frozen=True)
class MonitorRequest:
    request_id: str
    user_query: str
    targets: list[str] = field(default_factory=list)
    aliases: dict[str, list[str]] = field(default_factory=dict)
    time_window: dict[str, str] = field(default_factory=dict)
    source_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchTask:
    task_id: str
    path_type: str
    query: str
    source_class: str
    priority: int
    freshness_days: int
    expected_event_types: list[str]
    inclusion_domains: list[str] = field(default_factory=list)
    exclusion_domains: list[str] = field(default_factory=list)
    max_results: int = DEFAULTS["max_results"]


def _task_id(request_id: str, path_type: str, query: str) -> str:
    payload = f"{request_id}|{path_type}|{query}".encode("utf-8")
    return sha1(payload).hexdigest()[:16]


def _expand_aliases(request: MonitorRequest) -> dict[str, list[str]]:
    expanded: dict[str, list[str]] = {}
    for target in request.targets:
        candidates = [target, *request.aliases.get(target, [])]
        seen: set[str] = set()
        expanded[target] = []
        for c in candidates:
            canon = c.strip()
            if canon and canon.lower() not in seen:
                seen.add(canon.lower())
                expanded[target].append(canon)
    return expanded


def generate_search_plan(request: MonitorRequest) -> list[SearchTask]:
    """Generate path-based search tasks from request targets and aliases.

    For every target alias and search path, emits two query variants:
    - precision query (high-intent operators)
    - recall query (broader semantic net)
    """
    aliases_by_target = _expand_aliases(request)
    include_domains = request.source_constraints.get("include_domains", [])
    exclude_domains = request.source_constraints.get("exclude_domains", [])

    tasks: list[SearchTask] = []
    for path_type, cfg in PATH_CONFIG.items():
        for target, aliases in aliases_by_target.items():
            domain = request.source_constraints.get("target_domains", {}).get(target, "")
            for alias in aliases:
                for variant in ("precision_pattern", "recall_pattern"):
                    query = cfg[variant].format(target=alias, domain=domain).replace("site: ", "")
                    tasks.append(
                        SearchTask(
                            task_id=_task_id(request.request_id, path_type, query),
                            path_type=path_type,
                            query=query,
                            source_class=cfg.get("source_class", "web"),
                            priority=int(cfg.get("priority", DEFAULTS["priority"])),
                            freshness_days=int(cfg.get("freshness_days", DEFAULTS["freshness_days"])),
                            expected_event_types=list(cfg.get("expected_event_types", [])),
                            inclusion_domains=list(include_domains),
                            exclusion_domains=list(exclude_domains),
                            max_results=int(cfg.get("max_results", DEFAULTS["max_results"])),
                        )
                    )

    deduped: dict[tuple[str, str], SearchTask] = {}
    for task in tasks:
        deduped[(task.path_type, task.query.lower())] = task
    return list(deduped.values())


def rank_and_budget(tasks: list[SearchTask], max_tasks: int) -> list[SearchTask]:
    """Rank tasks by priority/freshness and cap to max_tasks.

    Higher priority first; for ties, prefer fresher windows (smaller days),
    then higher max_results as a breadth tie-breaker.
    """
    ranked = sorted(
        tasks,
        key=lambda t: (-t.priority, t.freshness_days, -t.max_results, t.task_id),
    )
    if max_tasks <= 0:
        return []
    return ranked[:max_tasks]
