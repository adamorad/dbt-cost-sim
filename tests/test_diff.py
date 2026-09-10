from __future__ import annotations

from dbt_cost_sim.diff import diff_models
from dbt_cost_sim.manifest import load_compiled_models


def test_diff_finds_modified_and_added_models(base_manifest_path, target_manifest_path):
    base = load_compiled_models(base_manifest_path)
    target = load_compiled_models(target_manifest_path)

    changed = diff_models(base, target)
    by_id = {c.unique_id: c for c in changed}

    assert set(by_id) == {"model.fixtures.modified_model", "model.fixtures.new_model"}
    assert by_id["model.fixtures.modified_model"].change_type == "modified"
    assert by_id["model.fixtures.new_model"].change_type == "added"


def test_unchanged_model_is_excluded(base_manifest_path, target_manifest_path):
    base = load_compiled_models(base_manifest_path)
    target = load_compiled_models(target_manifest_path)

    changed = diff_models(base, target)

    assert "model.fixtures.unchanged_model" not in {c.unique_id for c in changed}


def test_added_model_has_no_base_sql(base_manifest_path, target_manifest_path):
    base = load_compiled_models(base_manifest_path)
    target = load_compiled_models(target_manifest_path)

    changed = diff_models(base, target)
    new_model = next(c for c in changed if c.unique_id == "model.fixtures.new_model")

    assert new_model.base_sql is None
    assert new_model.target_sql == "select * from raw.events"


def test_removed_model_excluded_from_diff(tmp_path):
    base_path = tmp_path / "base.json"
    target_path = tmp_path / "target.json"
    base_path.write_text(
        '{"nodes": {"model.x.gone": {"resource_type": "model", "name": "gone", '
        '"compiled_code": "select 1"}}}'
    )
    target_path.write_text('{"nodes": {}}')

    changed = diff_models(load_compiled_models(base_path), load_compiled_models(target_path))

    assert changed == []
