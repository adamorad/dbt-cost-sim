"""Estimate BigQuery cost deltas for a list of changed dbt models."""

from __future__ import annotations

from dataclasses import dataclass

from dbt_cost_sim.bigquery_cost import DryRunClient, DryRunError, bytes_to_usd
from dbt_cost_sim.diff import ChangedModel


@dataclass(frozen=True)
class ModelCostEstimate:
    unique_id: str
    name: str
    change_type: str
    base_bytes: int | None
    target_bytes: int | None
    base_usd: float | None
    target_usd: float | None
    delta_usd: float | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def estimate_changed_models(
    changed: list[ChangedModel],
    client: DryRunClient,
    price_per_tib_usd: float,
) -> list[ModelCostEstimate]:
    """Dry-run each changed model's SQL and compute its cost delta.

    A model whose dry-run fails (e.g. it references a table that doesn't
    exist in the dry-run project) is reported with `error` set rather than
    raised, so one bad model doesn't abort the whole report.
    """
    results: list[ModelCostEstimate] = []
    for model in changed:
        try:
            target_bytes = client.total_bytes_processed(model.target_sql)
            target_usd = bytes_to_usd(target_bytes, price_per_tib_usd)

            base_bytes: int | None = None
            base_usd: float | None = None
            if model.base_sql is not None:
                base_bytes = client.total_bytes_processed(model.base_sql)
                base_usd = bytes_to_usd(base_bytes, price_per_tib_usd)

            delta_usd = target_usd - base_usd if base_usd is not None else target_usd

            results.append(
                ModelCostEstimate(
                    unique_id=model.unique_id,
                    name=model.name,
                    change_type=model.change_type,
                    base_bytes=base_bytes,
                    target_bytes=target_bytes,
                    base_usd=base_usd,
                    target_usd=target_usd,
                    delta_usd=delta_usd,
                )
            )
        except DryRunError as exc:
            results.append(
                ModelCostEstimate(
                    unique_id=model.unique_id,
                    name=model.name,
                    change_type=model.change_type,
                    base_bytes=None,
                    target_bytes=None,
                    base_usd=None,
                    target_usd=None,
                    delta_usd=None,
                    error=str(exc),
                )
            )
    return results
