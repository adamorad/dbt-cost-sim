from __future__ import annotations

from pathlib import Path

import pytest

from dbt_cost_sim.bigquery_cost import DryRunError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeDryRunClient:
    """A DryRunClient double: bytes proportional to SQL length, or scripted errors.

    Deterministic and dependency-free, so tests never need real GCP credentials.
    """

    def __init__(self, bytes_per_char: int = 100, error_for_sql_containing: str | None = None):
        self.bytes_per_char = bytes_per_char
        self.error_for_sql_containing = error_for_sql_containing
        self.calls: list[str] = []

    def total_bytes_processed(self, sql: str) -> int:
        self.calls.append(sql)
        if self.error_for_sql_containing and self.error_for_sql_containing in sql:
            raise DryRunError(
                f"simulated dry-run failure for query containing {self.error_for_sql_containing!r}"
            )
        return len(sql) * self.bytes_per_char


@pytest.fixture
def fake_client() -> FakeDryRunClient:
    return FakeDryRunClient()


@pytest.fixture
def base_manifest_path() -> Path:
    return FIXTURES_DIR / "manifest_base.json"


@pytest.fixture
def target_manifest_path() -> Path:
    return FIXTURES_DIR / "manifest_target.json"
