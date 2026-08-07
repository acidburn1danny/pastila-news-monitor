"""Pure deterministic HTML rendering for private Scout reports."""

from html import escape

from .models import _DesktopScoutReportInputV1, _reconstruct_report_input


def _render_report_html_v1(*, report: _DesktopScoutReportInputV1) -> str:
    value = _reconstruct_report_input(report)
    fields = (
        ("Operation reference", value.operation_reference),
        ("Status", value.status.value),
        ("Period days", str(value.executed_period_days)),
        ("Category", value.executed_category.value),
        ("Sources checked", str(value.sources_checked)),
        ("Sources succeeded", str(value.sources_succeeded)),
        ("Sources failed", str(value.sources_failed)),
        ("Articles found", str(value.articles_found)),
        ("Articles inserted", str(value.articles_inserted)),
        ("Duplicates skipped", str(value.duplicates_skipped)),
    )
    rows = "".join(
        f"<dt>{escape(label)}</dt><dd>{escape(item)}</dd>" for label, item in fields
    )
    failures = "".join(f"<li>{escape(item)}</li>" for item in value.failed_source_ids)
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Scout report</title></head><body><main><h1>Scout report</h1><dl>{rows}</dl><h2>Failed sources</h2><ul>{failures}</ul></main></body></html>'


__all__: tuple[str, ...] = ()
