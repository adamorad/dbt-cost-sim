"""Command-line entry point for dbt-cost-sim."""

from __future__ import annotations

import argparse
import sys

from dbt_cost_sim.bigquery_cost import DEFAULT_PRICE_PER_TIB_USD, BigQueryDryRunClient
from dbt_cost_sim.diff import diff_models
from dbt_cost_sim.estimate import estimate_changed_models
from dbt_cost_sim.manifest import load_compiled_models
from dbt_cost_sim.report import render_markdown, render_text


def _add_common_estimate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--gcp-project",
        help="GCP project to run dry-run queries against (defaults to application-default credentials' project)",
    )
    parser.add_argument("--location", help="BigQuery job location, e.g. US or EU")
    parser.add_argument(
        "--price-per-tib",
        type=float,
        default=DEFAULT_PRICE_PER_TIB_USD,
        help=f"On-demand price per TiB scanned, USD (default: {DEFAULT_PRICE_PER_TIB_USD})",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown"],
        default="text",
        help="Output format (default: text)",
    )


def _run_estimate(base_manifest: str, target_manifest: str, args: argparse.Namespace) -> int:
    base_models = load_compiled_models(base_manifest)
    target_models = load_compiled_models(target_manifest)
    changed = diff_models(base_models, target_models)

    if not changed:
        print("No cost-relevant model changes detected.")
        return 0

    client = BigQueryDryRunClient(project=args.gcp_project, location=args.location)
    estimates = estimate_changed_models(changed, client, args.price_per_tib)

    renderer = render_markdown if args.format == "markdown" else render_text
    print(renderer(estimates))

    return 1 if any(not e.ok for e in estimates) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dbt-cost-sim",
        description="Estimate the BigQuery cost delta of a dbt model change before you merge.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two already-compiled dbt manifest.json files",
    )
    diff_parser.add_argument("--base", required=True, help="Path to the base ref's manifest.json")
    diff_parser.add_argument(
        "--target", required=True, help="Path to the target ref's manifest.json"
    )
    _add_common_estimate_args(diff_parser)

    diff_refs_parser = subparsers.add_parser(
        "diff-refs",
        help="Compile a dbt project at two git refs, then diff (requires dbt and git on PATH)",
    )
    diff_refs_parser.add_argument(
        "--repo-dir", default=".", help="Path to the git repo root (default: .)"
    )
    diff_refs_parser.add_argument(
        "--project-subdir",
        default=".",
        help="Path to the dbt project within the repo, relative to --repo-dir (default: .)",
    )
    diff_refs_parser.add_argument(
        "--base-ref", required=True, help="Git ref to compile as the 'before' state"
    )
    diff_refs_parser.add_argument(
        "--target-ref", required=True, help="Git ref to compile as the 'after' state"
    )
    diff_refs_parser.add_argument("--dbt-target", help="dbt target profile to compile with")
    _add_common_estimate_args(diff_refs_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "diff":
        return _run_estimate(args.base, args.target, args)

    if args.command == "diff-refs":
        from dbt_cost_sim.git_compile import CompileError, compile_manifest_at_ref

        try:
            base_manifest = compile_manifest_at_ref(
                args.repo_dir, args.project_subdir, args.base_ref, args.dbt_target
            )
            target_manifest = compile_manifest_at_ref(
                args.repo_dir, args.project_subdir, args.target_ref, args.dbt_target
            )
        except CompileError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        return _run_estimate(str(base_manifest), str(target_manifest), args)

    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable — parser.error() exits the process


if __name__ == "__main__":
    sys.exit(main())
