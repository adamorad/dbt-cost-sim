# dbt-cost-sim

[![CI](https://github.com/adamorad/dbt-cost-sim/actions/workflows/ci.yml/badge.svg)](https://github.com/adamorad/dbt-cost-sim/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dbt-cost-sim.svg)](https://pypi.org/project/dbt-cost-sim/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Know what a dbt model change will cost **before** you merge it.

`dbt-cost-sim` compares a dbt project's *compiled* SQL between two states (a base ref and a target ref), and for every model whose SQL actually changed, uses BigQuery's [dry-run](https://cloud.google.com/bigquery/docs/dry-run-queries) API to estimate the bytes it will scan — and therefore its on-demand cost — without running the query or touching any data.

```
MODEL             CHANGE    BASE $     TARGET $   DELTA $
fct_orders        modified  $12.4000   $41.8000   +$29.4000
stg_events__raw    added    n/a        $3.1200    +$3.1200

Total estimated delta: +$32.5200
```

## Why

FinOps tools see cost, not lineage. Data catalogs see lineage, not cost. Neither tells you, at PR time, "this change to `fct_orders` is going to cost an extra $30/day." `dbt-cost-sim` closes that gap for BigQuery + dbt: a cheap, git-native check you can run locally or in CI, using BigQuery's own dry-run planner as the source of truth — no query execution, no historical-data guesswork.

## How it works

1. Load two dbt `manifest.json` artifacts (produced by `dbt compile`) — one for the base ref, one for the target ref.
2. Diff their compiled model SQL. A model is "changed" if its compiled SQL is new or different; unchanged models are skipped entirely.
3. For each changed model, submit its compiled SQL to BigQuery with `dry_run=True`. BigQuery resolves the query plan against real table metadata and returns `totalBytesProcessed` — without scanning any data or incurring cost.
4. Convert bytes to USD via on-demand pricing (default $6.25/TiB, configurable) and report the per-model delta, sorted by biggest increase first.

**Scope note (v1):** only models whose own compiled SQL changed are estimated. A change to an upstream model can also shift cost in downstream models that didn't change their own SQL (e.g. `select *` scanning a newly-added column) — that ripple effect is out of scope for v1 and tracked as future work.

## Install

```sh
pip install dbt-cost-sim
```

Not yet on PyPI — the release pipeline is wired up (see [Releasing](#releasing)) but no version has been published yet. Until then, install from GitHub:

```sh
pip install git+https://github.com/adamorad/dbt-cost-sim.git
# or, for local development:
uv sync
```

Requires BigQuery credentials the tool can use for dry-run queries — [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) (`gcloud auth application-default login`, or a service account in CI) with `bigquery.jobs.create` on the target project. Dry-run queries are free and never scan billable data.

## Usage

### `diff` — compare two already-compiled manifests

Use this if your CI already runs `dbt compile` for both refs (most CI setups do, e.g. via `dbt compile` in a matrix job or slim CI):

```sh
dbt-cost-sim diff \
  --base target-main/manifest.json \
  --target target-pr/manifest.json \
  --gcp-project my-gcp-project
```

### `diff-refs` — compile both refs for you

A convenience wrapper for local use: checks out each git ref into a disposable `git worktree`, runs `dbt compile` in each, then diffs. Requires `git` and `dbt` on `PATH`.

```sh
dbt-cost-sim diff-refs \
  --repo-dir . \
  --base-ref main \
  --target-ref HEAD \
  --gcp-project my-gcp-project
```

### Options (both commands)

| Flag | Default | Description |
|---|---|---|
| `--gcp-project` | ADC's default project | GCP project to run dry-run queries against |
| `--location` | none | BigQuery job location (e.g. `US`, `EU`) |
| `--price-per-tib` | `6.25` | On-demand price per TiB scanned, USD |
| `--format` | `text` | `text` or `markdown` (markdown suits a CI job summary or PR comment) |

Exit code is `1` if any model's dry-run failed (e.g. it references a table that doesn't exist yet in the dry-run project) — that model is still reported, with its error message, rather than aborting the whole run.

## Using it in CI

```yaml
# .github/workflows/cost-check.yml
name: dbt cost check
on: pull_request

jobs:
  cost-check:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # for Workload Identity Federation to GCP
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v3
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - run: uv tool install dbt-cost-sim
      - run: |
          dbt-cost-sim diff-refs \
            --repo-dir . \
            --base-ref "origin/${{ github.base_ref }}" \
            --target-ref "${{ github.sha }}" \
            --format markdown >> "$GITHUB_STEP_SUMMARY"
```

A dedicated composite GitHub Action that posts this as a PR comment is a natural next step — not built yet (see Roadmap).

## Development

```sh
mise install && uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy
```

All core logic (manifest parsing, diffing, cost math) is unit-tested against a `DryRunClient` protocol with a fake implementation — no real GCP credentials are needed to run the test suite. `git_compile.py` (the `diff-refs` orchestration) is tested against a real temporary git repo with a stubbed `dbt` binary.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit changes.

## Releasing

Publishing to PyPI uses [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token is stored in the repo. One-time setup, for maintainers:

1. On [pypi.org](https://pypi.org), under your account's Publishing settings, add a **pending publisher** for a new project named `dbt-cost-sim`: owner `adamorad`, repository `dbt-cost-sim`, workflow `release.yml`, environment `pypi`.
2. In this repo's GitHub settings, create an environment named `pypi` (optionally with required reviewers, for an extra approval gate before publishing).

After that, cutting a release is: bump `version` in `pyproject.toml`, then create a GitHub Release (tag `vX.Y.Z`). The [release workflow](.github/workflows/release.yml) runs the full test/lint/type-check suite, builds the package, and publishes to PyPI automatically.

## Roadmap

- [ ] Optional downstream ripple-effect estimation (one hop, opt-in)
- [ ] Composite GitHub Action that posts results as a PR comment
- [ ] Snowflake support (credit-based, needs a different cost model than BigQuery's bytes-scanned)

## Structure

```
src/dbt_cost_sim/
  manifest.py      — parse dbt manifest.json into model -> compiled SQL
  diff.py           — find models whose compiled SQL changed between two manifests
  bigquery_cost.py  — BigQuery dry-run client + bytes -> USD conversion
  estimate.py       — tie diff + dry-run together into per-model cost deltas
  report.py         — render text/Markdown reports
  git_compile.py    — git worktree + `dbt compile` orchestration for `diff-refs`
  cli.py            — argparse entry point
tests/              — unit tests (fixtures under tests/fixtures/)
docs/               — documentation
archive/            — parked old work
.github/workflows/  — CI (test/lint/type-check) and release (build + PyPI publish)
CHANGES.md          — notable changes
CLAUDE.md           — agent behavioral rules + project notes
CONTRIBUTING.md     — how to submit changes
SECURITY.md         — vulnerability reporting
```

## License

MIT — see [LICENSE](LICENSE).
