from __future__ import annotations

import json
from pathlib import Path
from typing import Type

from pydantic import BaseModel

from .models import (
    CompanyClaim,
    DailyDigest,
    DocumentRecord,
    EvidenceItem,
    MonitorRequest,
    RunMetrics,
    SearchCandidate,
    SearchTask,
)

CONTRACT_MODELS: tuple[Type[BaseModel], ...] = (
    MonitorRequest,
    SearchTask,
    SearchCandidate,
    DocumentRecord,
    EvidenceItem,
    CompanyClaim,
    DailyDigest,
    RunMetrics,
)


def schema_for(model: Type[BaseModel]) -> dict:
    return model.model_json_schema()


def all_schemas() -> dict[str, dict]:
    return {model.__name__: schema_for(model) for model in CONTRACT_MODELS}


def write_schemas(output_dir: str | Path) -> list[Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for model in CONTRACT_MODELS:
        file_path = target / f"{model.__name__}.schema.json"
        file_path.write_text(json.dumps(schema_for(model), indent=2), encoding="utf-8")
        written.append(file_path)

    index_path = target / "contracts.schemas.json"
    index_path.write_text(json.dumps(all_schemas(), indent=2), encoding="utf-8")
    written.append(index_path)

    return written
