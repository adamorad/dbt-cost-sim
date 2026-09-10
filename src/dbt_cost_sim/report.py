"""Render cost estimates as plain-text and Markdown reports."""

from __future__ import annotations

from dbt_cost_sim.estimate import ModelCostEstimate


def _fmt_usd(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}${value:,.4f}"


def _sort_key(estimate: ModelCostEstimate) -> tuple[bool, float]:
    # Errors and unscored rows sort last; otherwise biggest cost increase first.
    return (estimate.delta_usd is None, -(estimate.delta_usd or 0.0))


def render_text(estimates: list[ModelCostEstimate]) -> str:
    """Render a plain-text table for terminal output."""
    if not estimates:
        return "No cost-relevant model changes detected."

    header = ("MODEL", "CHANGE", "BASE $", "TARGET $", "DELTA $")
    rows: list[tuple[str, str, str, str, str]] = [header]
    for e in sorted(estimates, key=_sort_key):
        if e.error:
            rows.append((e.name, e.change_type, "ERROR", "ERROR", e.error))
            continue
        base = "n/a" if e.base_usd is None else f"${e.base_usd:,.4f}"
        rows.append((e.name, e.change_type, base, f"${e.target_usd:,.4f}", _fmt_usd(e.delta_usd)))

    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    lines = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows]

    total_delta = sum(e.delta_usd for e in estimates if e.delta_usd is not None)
    lines.append("")
    lines.append(f"Total estimated delta: {_fmt_usd(total_delta)}")
    return "\n".join(lines)


def render_markdown(estimates: list[ModelCostEstimate]) -> str:
    """Render a Markdown table, suitable for a CI job summary or PR comment."""
    if not estimates:
        return "No cost-relevant model changes detected."

    lines = ["| Model | Change | Base | Target | Delta |", "|---|---|---|---|---|"]
    for e in sorted(estimates, key=_sort_key):
        if e.error:
            lines.append(f"| {e.name} | {e.change_type} | ⚠️ | ⚠️ | {e.error} |")
            continue
        base = "n/a" if e.base_usd is None else f"${e.base_usd:,.4f}"
        lines.append(
            f"| {e.name} | {e.change_type} | {base} | ${e.target_usd:,.4f} | {_fmt_usd(e.delta_usd)} |"
        )

    total_delta = sum(e.delta_usd for e in estimates if e.delta_usd is not None)
    lines.append("")
    lines.append(f"**Total estimated delta: {_fmt_usd(total_delta)}**")
    return "\n".join(lines)
