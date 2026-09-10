from __future__ import annotations

import pytest

from dbt_cost_sim.bigquery_cost import BYTES_PER_TIB, bytes_to_usd


def test_bytes_to_usd_at_default_price():
    assert bytes_to_usd(BYTES_PER_TIB) == pytest.approx(6.25)


def test_bytes_to_usd_zero_bytes_is_free():
    assert bytes_to_usd(0) == 0.0


def test_bytes_to_usd_custom_price():
    assert bytes_to_usd(BYTES_PER_TIB, price_per_tib_usd=5.0) == pytest.approx(5.0)


def test_fake_client_scales_with_query_length(fake_client):
    short = fake_client.total_bytes_processed("select 1")
    long = fake_client.total_bytes_processed("select 1, 2, 3, 4, 5, 6, 7, 8, 9, 10")

    assert long > short
    assert fake_client.calls == ["select 1", "select 1, 2, 3, 4, 5, 6, 7, 8, 9, 10"]
