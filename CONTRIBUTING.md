# Contributing

Thanks for considering a contribution to dbt-cost-sim.

## Setup

```sh
git clone https://github.com/adamorad/dbt-cost-sim.git
cd dbt-cost-sim
mise install && uv sync
```

## Before opening a PR

```sh
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest -v
```

All four run in CI on every PR; a PR that fails any of them won't be mergeable.

## Guidelines

- Keep changes focused — one logical change per PR.
- New behavior needs a test. `git_compile.py` is tested against a real temporary
  git repo with a stubbed `dbt` binary (see `tests/test_git_compile.py`); the
  rest of the core logic is tested against the `DryRunClient` protocol with a
  fake implementation (see `tests/conftest.py`) — no real GCP credentials
  needed for any of it.
- If you're changing the cost model or the diffing semantics, update the
  README's "How it works" section to match.
- Bug fixes and small improvements: open a PR directly. Larger changes
  (new subcommands, changing the CLI's public interface, new cloud/warehouse
  support): open an issue first to discuss the approach.

## Reporting a security issue

See [SECURITY.md](SECURITY.md) — please don't open a public issue for
security vulnerabilities.
