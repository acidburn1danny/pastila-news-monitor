from __future__ import annotations

from .models import EditorialObservationV1


def render_observation_report_v1(value: EditorialObservationV1) -> str:
    """Render a local inspection surface; no provider or preference projection."""
    lines = [
        "# Evidență editare proprietar",
        "",
        f"Capture: `{value.capture_id}`",
        f"Eveniment: `{value.metadata.event_id}`",
        f"Finalizat: `{'DA' if value.final else 'NU'}`",
        "",
        "## Text generat inițial",
        "",
        value.generated.text,
    ]
    if value.final is None:
        return "\n".join(lines).rstrip() + "\n"
    lines.extend(
        ("", "## Text final proprietar", "", value.final.text, "", "## Diferențe", "")
    )
    for index, item in enumerate(value.diff):
        lines.append(
            f"- {index}: `{item.operation.value}` / `{item.severity}` / `{item.proposed_class.value}`"
        )
    if value.kpi:
        lines.extend(
            (
                "",
                "## Utilitate editorială",
                "",
                f"- Scor parțial normalizat: `{value.kpi.score}`",
                f"- Completitudine: `{value.kpi.completeness}`",
                f"- Încredere: `{value.kpi.confidence}`",
                f"- Corecție factuală critică: `{'DA' if value.kpi.critical_factual_issue else 'NU'}`",
            )
        )
    if value.expression_evidence:
        lines.extend(("", "## Expresii observate", ""))
        lines.extend(
            f"- `{item.authority_id}`: `{item.outcome}`"
            for item in value.expression_evidence
        )
    return "\n".join(lines).rstrip() + "\n"
