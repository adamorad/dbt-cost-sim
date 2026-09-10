from __future__ import annotations

import pytest

from dbt_cost_sim import cli


def test_build_parser_requires_a_subcommand():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_diff_subcommand_parses_required_args():
    parser = cli.build_parser()
    args = parser.parse_args(["diff", "--base", "base.json", "--target", "target.json"])

    assert args.command == "diff"
    assert args.base == "base.json"
    assert args.target == "target.json"
    assert args.format == "text"


def test_diff_refs_subcommand_parses_required_args():
    parser = cli.build_parser()
    args = parser.parse_args(
        ["diff-refs", "--base-ref", "main", "--target-ref", "HEAD", "--project-subdir", "warehouse"]
    )

    assert args.command == "diff-refs"
    assert args.base_ref == "main"
    assert args.target_ref == "HEAD"
    assert args.project_subdir == "warehouse"


def test_main_diff_end_to_end(
    monkeypatch, capsys, fake_client, base_manifest_path, target_manifest_path
):
    monkeypatch.setattr(
        cli, "BigQueryDryRunClient", lambda project=None, location=None: fake_client
    )

    exit_code = cli.main(
        ["diff", "--base", str(base_manifest_path), "--target", str(target_manifest_path)]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "modified_model" in out
    assert "new_model" in out
    assert "Total estimated delta" in out


def test_main_diff_no_changes_short_circuits_before_bigquery(monkeypatch, capsys, tmp_path):
    def _boom(*args, **kwargs):
        raise AssertionError("should not construct a BigQuery client when there are no changes")

    monkeypatch.setattr(cli, "BigQueryDryRunClient", _boom)

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"nodes": {"model.x.m": {"resource_type": "model", "name": "m", '
        '"compiled_code": "select 1"}}}'
    )

    exit_code = cli.main(["diff", "--base", str(manifest), "--target", str(manifest)])

    assert exit_code == 0
    assert "No cost-relevant model changes detected." in capsys.readouterr().out


def test_main_diff_nonzero_exit_when_a_model_errors(
    monkeypatch, capsys, fake_client, base_manifest_path, tmp_path
):
    fake_client.error_for_sql_containing = "raw.orders"
    monkeypatch.setattr(
        cli, "BigQueryDryRunClient", lambda project=None, location=None: fake_client
    )

    target = tmp_path / "target.json"
    target.write_text(
        '{"nodes": {"model.x.m": {"resource_type": "model", "name": "m", '
        '"compiled_code": "select * from raw.orders"}}}'
    )

    exit_code = cli.main(["diff", "--base", str(base_manifest_path), "--target", str(target)])

    assert exit_code == 1
