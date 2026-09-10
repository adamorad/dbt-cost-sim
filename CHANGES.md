# Changes

## Unreleased
- Initial scaffold (2026-09-10).
- v0.1.0: core `dbt-cost-sim` CLI — `diff` (compare two compiled dbt manifests)
  and `diff-refs` (compile a dbt project at two git refs via a scratch
  worktree, then diff). Cost estimation via BigQuery dry-run, text/Markdown
  reporting, 29 unit tests against a fake `DryRunClient` (2026-09-10).
