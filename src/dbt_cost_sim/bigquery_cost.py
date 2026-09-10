"""BigQuery dry-run based cost estimation.

Dry-run queries are free and never scan data — BigQuery's planner resolves
referenced table metadata and returns the bytes it *would* scan, without
executing anything. That's what makes pre-merge cost estimation possible: no
query runs, no data moves, and it's usable directly on compiled dbt SQL as
long as the referenced tables already exist in the target project.
"""

from __future__ import annotations

from typing import Protocol

DEFAULT_PRICE_PER_TIB_USD = 6.25  # BigQuery on-demand pricing (US), as of 2026
BYTES_PER_TIB = 1024**4


class DryRunClient(Protocol):
    """Minimal interface this module needs from a BigQuery client.

    Implemented by BigQueryDryRunClient (wraps google-cloud-bigquery) for real
    use, and by a fake in tests — keeps the diff/cost math testable without
    real GCP credentials.
    """

    def total_bytes_processed(self, sql: str) -> int:
        """Return the bytes BigQuery would scan for `sql`, without running it."""
        ...


class DryRunError(RuntimeError):
    """Raised when BigQuery can't dry-run a query (e.g. a bad reference)."""


class BigQueryDryRunClient:
    """Thin wrapper around google-cloud-bigquery for dry-run byte estimates."""

    def __init__(self, project: str | None = None, location: str | None = None):
        from google.cloud import bigquery  # deferred: heavy, optional at import time

        self._bigquery = bigquery
        self._client = bigquery.Client(project=project, location=location)

    def total_bytes_processed(self, sql: str) -> int:
        from google.api_core.exceptions import GoogleAPIError

        job_config = self._bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        try:
            job = self._client.query(sql, job_config=job_config)
        except GoogleAPIError as exc:
            raise DryRunError(str(exc)) from exc
        return job.total_bytes_processed


def bytes_to_usd(num_bytes: int, price_per_tib_usd: float = DEFAULT_PRICE_PER_TIB_USD) -> float:
    """Convert a byte count to an estimated USD cost at on-demand pricing."""
    return (num_bytes / BYTES_PER_TIB) * price_per_tib_usd
