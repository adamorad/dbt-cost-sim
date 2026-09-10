from __future__ import annotations

from dbt_cost_sim.diff import ChangedModel
from dbt_cost_sim.estimate import estimate_changed_models


def test_estimate_modified_model_computes_delta(fake_client):
    changed = [
        ChangedModel(
            unique_id="model.x.m",
            name="m",
            change_type="modified",
            base_sql="select 1",
            target_sql="select 1, 2, 3",
        )
    ]

    [result] = estimate_changed_models(changed, fake_client, price_per_tib_usd=6.25)

    assert result.ok
    assert result.base_bytes is not None
    assert result.target_bytes is not None
    assert result.target_bytes > result.base_bytes
    assert result.delta_usd == result.target_usd - result.base_usd


def test_estimate_added_model_has_no_base_cost(fake_client):
    changed = [
        ChangedModel(
            unique_id="model.x.new",
            name="new",
            change_type="added",
            base_sql=None,
            target_sql="select * from raw.events",
        )
    ]

    [result] = estimate_changed_models(changed, fake_client, price_per_tib_usd=6.25)

    assert result.ok
    assert result.base_bytes is None
    assert result.base_usd is None
    assert result.delta_usd == result.target_usd


def test_estimate_reports_dry_run_error_without_raising(fake_client):
    fake_client.error_for_sql_containing = "bad_table"
    changed = [
        ChangedModel(
            unique_id="model.x.broken",
            name="broken",
            change_type="modified",
            base_sql="select 1",
            target_sql="select * from bad_table",
        )
    ]

    [result] = estimate_changed_models(changed, fake_client, price_per_tib_usd=6.25)

    assert not result.ok
    assert result.error is not None
    assert result.delta_usd is None


def test_one_bad_model_does_not_abort_the_rest(fake_client):
    fake_client.error_for_sql_containing = "bad_table"
    changed = [
        ChangedModel("model.x.broken", "broken", "modified", "select 1", "select * from bad_table"),
        ChangedModel("model.x.fine", "fine", "modified", "select 1", "select 1, 2"),
    ]

    results = estimate_changed_models(changed, fake_client, price_per_tib_usd=6.25)
    by_id = {r.unique_id: r for r in results}

    assert not by_id["model.x.broken"].ok
    assert by_id["model.x.fine"].ok
