"""Diff two sets of compiled dbt models to find what changed."""

from __future__ import annotations

from dataclasses import dataclass

from dbt_cost_sim.manifest import CompiledModel


@dataclass(frozen=True)
class ChangedModel:
    unique_id: str
    name: str
    change_type: str  # "added" or "modified"
    base_sql: str | None
    target_sql: str


def diff_models(
    base_models: dict[str, CompiledModel],
    target_models: dict[str, CompiledModel],
) -> list[ChangedModel]:
    """Return models whose compiled SQL is new or different in target vs base.

    Removed models (present in base, absent in target) carry no cost in the
    target state and are intentionally excluded — there's nothing to estimate.
    Ripple effects on unchanged downstream models are out of scope for v1.
    """
    changed: list[ChangedModel] = []
    for unique_id, target in sorted(target_models.items()):
        base = base_models.get(unique_id)
        if base is None:
            changed.append(
                ChangedModel(
                    unique_id=unique_id,
                    name=target.name,
                    change_type="added",
                    base_sql=None,
                    target_sql=target.compiled_sql,
                )
            )
        elif base.compiled_sql != target.compiled_sql:
            changed.append(
                ChangedModel(
                    unique_id=unique_id,
                    name=target.name,
                    change_type="modified",
                    base_sql=base.compiled_sql,
                    target_sql=target.compiled_sql,
                )
            )
    return changed
