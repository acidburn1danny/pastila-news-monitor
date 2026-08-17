from __future__ import annotations

import re
from difflib import SequenceMatcher
from statistics import median

from .models import (
    DiffOperationV1,
    DiffUnitV1,
    DimensionV1,
    EditClassV1,
    OwnerClassificationV1,
    UsabilityKpiV1,
)

_UNIT = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.UNICODE)
_WEIGHTS = {"C": 0.30, "S": 0.15, "M": 0.10, "F": 0.15, "Q": 0.15, "T": 0.15}
_RETENTION = {
    DiffOperationV1.RETAINED: 1.0,
    DiffOperationV1.LIGHT_EDIT: 0.75,
    DiffOperationV1.SUBSTANTIAL_EDIT: 0.25,
    DiffOperationV1.MOVED: 1.0,
    DiffOperationV1.DELETED: 0.0,
}


def _units(text: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in _UNIT.findall(text) if value.strip())


def _ratio(left: str, right: str) -> float:
    return round(
        SequenceMatcher(
            None, left.casefold().split(), right.casefold().split(), autojunk=False
        ).ratio(),
        6,
    )


def structured_diff_v1(generated: str, final: str) -> tuple[DiffUnitV1, ...]:
    before, after = _units(generated), _units(final)
    matcher = SequenceMatcher(None, before, after, autojunk=False)
    result: list[DiffUnitV1] = []
    deleted: list[tuple[int, str]] = []
    inserted: list[tuple[int, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.extend(
                DiffUnitV1(
                    operation=DiffOperationV1.RETAINED
                    if i == j
                    else DiffOperationV1.MOVED,
                    generated_index=i,
                    final_index=j,
                    generated_text=before[i],
                    final_text=after[j],
                    severity="NONE" if i == j else "MINOR",
                    similarity=1,
                    proposed_class=EditClassV1.UNKNOWN
                    if i == j
                    else EditClassV1.STRUCTURE,
                )
                for i, j in zip(range(i1, i2), range(j1, j2), strict=True)
            )
        elif tag == "replace":
            width = max(i2 - i1, j2 - j1)
            for offset in range(width):
                old = before[i1 + offset] if i1 + offset < i2 else None
                new = after[j1 + offset] if j1 + offset < j2 else None
                if old is None:
                    inserted.append((j1 + offset, new or ""))
                    continue
                if new is None:
                    deleted.append((i1 + offset, old))
                    continue
                similarity = _ratio(old, new)
                operation = (
                    DiffOperationV1.LIGHT_EDIT
                    if similarity >= 0.72
                    else DiffOperationV1.SUBSTANTIAL_EDIT
                )
                result.append(
                    DiffUnitV1(
                        operation=operation,
                        generated_index=i1 + offset,
                        final_index=j1 + offset,
                        generated_text=old,
                        final_text=new,
                        severity="MINOR"
                        if operation is DiffOperationV1.LIGHT_EDIT
                        else "MAJOR",
                        similarity=similarity,
                        proposed_class=EditClassV1.EXPRESSION_OR_WORDING
                        if operation is DiffOperationV1.LIGHT_EDIT
                        else EditClassV1.UNKNOWN,
                    )
                )
        elif tag == "delete":
            deleted.extend((i, before[i]) for i in range(i1, i2))
        elif tag == "insert":
            inserted.extend((j, after[j]) for j in range(j1, j2))
    used_inserted: set[int] = set()
    for old_index, old in deleted:
        moved = next(
            (
                (n, new_index)
                for n, (new_index, new) in enumerate(inserted)
                if n not in used_inserted and old == new
            ),
            None,
        )
        if moved:
            used_inserted.add(moved[0])
            result.append(
                DiffUnitV1(
                    operation=DiffOperationV1.MOVED,
                    generated_index=old_index,
                    final_index=moved[1],
                    generated_text=old,
                    final_text=old,
                    severity="MINOR",
                    similarity=1,
                    proposed_class=EditClassV1.STRUCTURE,
                )
            )
        else:
            result.append(
                DiffUnitV1(
                    operation=DiffOperationV1.DELETED,
                    generated_index=old_index,
                    generated_text=old,
                    severity="MAJOR",
                    similarity=0,
                    proposed_class=EditClassV1.UNKNOWN,
                )
            )
    for n, (new_index, new) in enumerate(inserted):
        if n not in used_inserted:
            result.append(
                DiffUnitV1(
                    operation=DiffOperationV1.INSERTED,
                    final_index=new_index,
                    final_text=new,
                    severity="MAJOR",
                    similarity=0,
                    proposed_class=EditClassV1.UNKNOWN,
                )
            )
    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.generated_index is None,
                item.generated_index
                if item.generated_index is not None
                else item.final_index or 0,
            ),
        )
    )


def analyze_pair_v1(
    generated: str,
    final: str,
    classifications: tuple[OwnerClassificationV1, ...] = (),
    *,
    mechanism_available: bool = False,
    active_edit_seconds: float | None = None,
) -> tuple[tuple[DiffUnitV1, ...], UsabilityKpiV1]:
    diff = structured_diff_v1(generated, final)
    generated_ops = [item for item in diff if item.generated_index is not None]
    c = sum(_RETENTION[item.operation] for item in generated_ops) / max(
        1, len(generated_ops)
    )
    moved_or_deleted = sum(
        item.operation in {DiffOperationV1.MOVED, DiffOperationV1.DELETED}
        for item in generated_ops
    )
    s = max(0.0, 1 - moved_or_deleted / max(1, len(generated_ops)))
    marked = {item.diff_index: item for item in classifications}
    factual = [
        item
        for item in marked.values()
        if item.edit_class
        in {EditClassV1.FACT_CORRECTION, EditClassV1.REMOVE_HALLUCINATION}
    ]
    changed_count = sum(item.operation is not DiffOperationV1.RETAINED for item in diff)
    fully_classified = changed_count > 0 and len(marked) >= changed_count
    f_value = (
        0.0
        if any(item.edit_class is EditClassV1.REMOVE_HALLUCINATION for item in factual)
        else 0.5
        if factual
        else 1.0
        if fully_classified
        else None
    )
    penalty = sum(
        1 if item.severity == "MINOR" else 3
        for item in diff
        if item.operation is not DiffOperationV1.RETAINED
    )
    q = max(0.0, 1 - penalty / (8 * max(1, len(_units(final)))))
    dimensions = {
        "C": DimensionV1(
            value=round(c, 6), available=True, reason="deterministic unit retention"
        ),
        "S": DimensionV1(
            value=round(s, 6), available=True, reason="unit deletion/movement burden"
        ),
        "M": DimensionV1(
            value=None,
            available=False,
            reason=(
                "generated mechanism authority exists but final retention is unclassified"
                if mechanism_available
                else "no reliable mechanism authority"
            ),
        ),
        "F": DimensionV1(
            value=f_value,
            available=f_value is not None,
            reason="owner factual classification"
            if f_value is not None
            else "factual status unknown; retention is not proof",
        ),
        "Q": DimensionV1(
            value=round(q, 6), available=True, reason="severity-weighted edit burden"
        ),
        "T": DimensionV1(
            value=None,
            available=False,
            reason="active edit time not captured without intrusive telemetry",
        ),
    }
    available_weight = sum(
        _WEIGHTS[key] for key, value in dimensions.items() if value.available
    )
    score = (
        100
        * sum(
            _WEIGHTS[key] * (value.value or 0)
            for key, value in dimensions.items()
            if value.available
        )
        / available_weight
    )
    coverage = len(marked) / max(1, changed_count)
    wholesale = c < 0.30 or sum(
        item.operation is DiffOperationV1.INSERTED for item in diff
    ) > len(generated_ops)
    band = (
        "poor"
        if score < 70
        else "usable skeleton"
        if score < 80
        else "strong draft"
        if score < 90
        else "target"
        if score <= 95
        else "excellent retention"
    )
    return diff, UsabilityKpiV1(
        score=round(score, 2),
        completeness=round(available_weight, 2),
        confidence="HIGH"
        if available_weight >= 0.85
        else "MEDIUM"
        if available_weight >= 0.60
        else "LOW",
        band=band,
        dimensions=dimensions,
        wholesale_replacement=wholesale,
        critical_factual_issue=any(
            item.edit_class is EditClassV1.REMOVE_HALLUCINATION for item in factual
        ),
        classification_coverage=round(min(1, coverage), 6),
    )


def aggregate_episode_v1(values: tuple[UsabilityKpiV1, ...]) -> dict[str, object]:
    scores = tuple(value.score for value in values if value.score is not None)
    return {
        "schema_version": 1,
        "measured_story_count": len(scores),
        "median_score": round(median(scores), 2) if scores else None,
        "mean_completeness": round(
            sum(value.completeness for value in values) / len(values), 3
        )
        if values
        else 0,
        "wholesale_replacement_rate": round(
            sum(value.wholesale_replacement for value in values) / len(values), 3
        )
        if values
        else None,
        "critical_factual_issue_count": sum(
            value.critical_factual_issue for value in values
        ),
    }
