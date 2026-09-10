"""Parse dbt manifest.json artifacts into a model -> compiled SQL mapping."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompiledModel:
    unique_id: str
    name: str
    compiled_sql: str


def load_compiled_models(manifest_path: str | Path) -> dict[str, CompiledModel]:
    """Load a dbt manifest.json and return its compiled models keyed by unique_id.

    Only nodes with resource_type == "model" and non-empty compiled SQL are
    included. dbt only populates compiled SQL after `dbt compile` or `dbt run`
    has processed the manifest, so a manifest.json produced by `dbt parse`
    alone will yield an empty result.
    """
    path = Path(manifest_path)
    data = json.loads(path.read_text())

    models: dict[str, CompiledModel] = {}
    for unique_id, node in data.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue
        # dbt >=1.3 uses "compiled_code"; earlier versions used "compiled_sql".
        sql = node.get("compiled_code") or node.get("compiled_sql")
        if not sql:
            continue
        models[unique_id] = CompiledModel(
            unique_id=unique_id,
            name=node.get("name", unique_id),
            compiled_sql=sql,
        )
    return models
