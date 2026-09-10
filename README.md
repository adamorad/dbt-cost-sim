# dbt-cost-sim

Diffs a dbt project's compiled SQL between two git refs and reports BigQuery cost deltas per changed model via dry-run, before you merge.

## Stack
python

## Setup
```sh
mise install && uv sync
cp .env.example .env  # fill in secrets
```

## Run
```sh
uv run src/main.py
```

## Structure
```
src/      — source code
tests/    — tests
docs/     — documentation
archive/  — parked old work
CHANGES.md  — notable changes
CLAUDE.md   — agent behavioral rules + project notes
SECURITY.md — vulnerability reporting
```
