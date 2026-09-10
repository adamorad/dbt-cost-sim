from __future__ import annotations

from dbt_cost_sim.estimate import ModelCostEstimate
from dbt_cost_sim.report import render_markdown, render_text


def _estimate(**overrides) -> ModelCostEstimate:
    defaults = {
        "unique_id": "model.x.m",
        "name": "m",
        "change_type": "modified",
        "base_bytes": 1_000,
        "target_bytes": 2_000,
        "base_usd": 0.01,
        "target_usd": 0.02,
        "delta_usd": 0.01,
        "error": None,
    }
    defaults.update(overrides)
    return ModelCostEstimate(**defaults)


def test_render_text_no_estimates():
    assert render_text([]) == "No cost-relevant model changes detected."


def test_render_markdown_no_estimates():
    assert render_markdown([]) == "No cost-relevant model changes detected."


def test_render_text_includes_model_name_and_total():
    text = render_text([_estimate(name="my_model")])

    assert "my_model" in text
    assert "Total estimated delta" in text


def test_render_text_shows_error_rows():
    text = render_text(
        [
            _estimate(
                name="broken",
                base_bytes=None,
                target_bytes=None,
                base_usd=None,
                target_usd=None,
                delta_usd=None,
                error="table not found",
            )
        ]
    )

    assert "broken" in text
    assert "table not found" in text


def test_render_markdown_is_a_table():
    md = render_markdown([_estimate(name="my_model")])

    assert md.startswith("| Model |")
    assert "my_model" in md
    assert "**Total estimated delta:" in md


def test_biggest_increase_sorts_first():
    small = _estimate(unique_id="model.x.small", name="small", delta_usd=0.001)
    big = _estimate(unique_id="model.x.big", name="big", delta_usd=10.0)

    text = render_text([small, big])

    assert text.index("big") < text.index("small")
