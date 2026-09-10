from __future__ import annotations

from dbt_cost_sim.manifest import load_compiled_models


def test_loads_only_models_with_compiled_sql(base_manifest_path):
    models = load_compiled_models(base_manifest_path)

    assert set(models) == {
        "model.fixtures.unchanged_model",
        "model.fixtures.modified_model",
    }


def test_excludes_non_model_resource_types(base_manifest_path):
    models = load_compiled_models(base_manifest_path)

    assert "test.fixtures.not_a_model" not in models


def test_excludes_models_without_compiled_code(base_manifest_path):
    models = load_compiled_models(base_manifest_path)

    assert "model.fixtures.not_yet_compiled" not in models


def test_model_fields(base_manifest_path):
    models = load_compiled_models(base_manifest_path)
    model = models["model.fixtures.unchanged_model"]

    assert model.unique_id == "model.fixtures.unchanged_model"
    assert model.name == "unchanged_model"
    assert model.compiled_sql == "select id, name from raw.customers"


def test_supports_legacy_compiled_sql_field(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"nodes": {"model.x.y": {"resource_type": "model", "name": "y", '
        '"compiled_sql": "select 1"}}}'
    )

    models = load_compiled_models(manifest)

    assert models["model.x.y"].compiled_sql == "select 1"
