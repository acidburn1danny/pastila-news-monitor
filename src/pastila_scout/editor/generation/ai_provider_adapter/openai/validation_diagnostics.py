"""Content-free structural diagnostics for OpenAI provider DTO failures."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

_BRANCHES = {
    "OpenAIRevisedTextComponent": "text_component",
    "OpenAIRevisedStoryComponent": "story_component",
    "OpenAIRevisedCallToActionComponent": "cta_component",
}
_FIELDS = {
    "component_type": "component_type",
    "component_reference": "component_reference",
    "revised_text": "text",
    "factual_summary": "factual_summary",
    "commentary_block_texts": "commentary_block_texts",
    "ending": "ending",
    "bridge_text": "cta_text",
}
_ERROR_TYPES = {
    "missing": "missing",
    "extra_forbidden": "extra_forbidden",
    "string_type": "string_type",
    "string_too_short": "string_too_short",
    "string_too_long": "string_too_long",
    "list_type": "list_type",
    "tuple_type": "list_type",
    "too_short": "too_short",
    "too_long": "too_long",
    "literal_error": "literal_error",
    "enum": "enum",
    "string_pattern_mismatch": "pattern_mismatch",
    "model_type": "model_type",
    "dict_type": "dict_type",
}


@dataclass(frozen=True, slots=True)
class SafeDTOValidationDiagnostics:
    total_error_count: int
    unique_error_category_count: int
    affected_component_count: int
    top_level_error_count: int
    nested_error_count: int
    model_validator_error_count: int
    union_branch_error_count: int
    error_type_histogram: tuple[tuple[str, int], ...]
    location_shape_histogram: tuple[tuple[str, int], ...]
    error_category_by_location_shape: tuple[tuple[str, str, int], ...]
    distinct_location_shape_count: int
    probable_primary_failure_category: str
    union_expansion_suspected: bool
    duplicate_reference_validator_triggered: bool
    single_component_concentration: bool
    multi_component_distribution: bool
    story_shape_count: int
    text_shape_count: int
    cta_shape_count: int
    ambiguous_shape_count: int
    unknown_shape_count: int

    def safe_metadata(self) -> tuple[tuple[str, str], ...]:
        """Serialize only repository-owned categories and aggregate counts."""

        return (
            ("validation_stage", "provider_dto"),
            ("total_error_count", str(self.total_error_count)),
            ("unique_error_category_count", str(self.unique_error_category_count)),
            ("affected_component_count", str(self.affected_component_count)),
            ("top_level_error_count", str(self.top_level_error_count)),
            ("nested_error_count", str(self.nested_error_count)),
            ("model_validator_error_count", str(self.model_validator_error_count)),
            ("union_branch_error_count", str(self.union_branch_error_count)),
            ("error_type_histogram", _json_pairs(self.error_type_histogram)),
            (
                "location_shape_histogram",
                _json_pairs(self.location_shape_histogram),
            ),
            (
                "error_category_by_location_shape",
                json.dumps(
                    [
                        {"category": category, "count": count, "location": location}
                        for location, category, count in self.error_category_by_location_shape
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
            ("distinct_location_shape_count", str(self.distinct_location_shape_count)),
            (
                "probable_primary_failure_category",
                self.probable_primary_failure_category,
            ),
            ("union_expansion_suspected", _yes_no(self.union_expansion_suspected)),
            (
                "duplicate_reference_validator_triggered",
                _yes_no(self.duplicate_reference_validator_triggered),
            ),
            (
                "single_component_concentration",
                _yes_no(self.single_component_concentration),
            ),
            (
                "multi_component_distribution",
                _yes_no(self.multi_component_distribution),
            ),
            ("story_shape_count", str(self.story_shape_count)),
            ("text_shape_count", str(self.text_shape_count)),
            ("cta_shape_count", str(self.cta_shape_count)),
            ("ambiguous_shape_count", str(self.ambiguous_shape_count)),
            ("unknown_shape_count", str(self.unknown_shape_count)),
        )


@dataclass(frozen=True, slots=True)
class _Error:
    raw_type: str
    location: str
    component_index: int | None
    branch: str | None


def build_safe_dto_validation_diagnostics(
    error: ValidationError,
) -> SafeDTOValidationDiagnostics:
    """Reduce Pydantic union errors without retaining inputs, values, or messages."""

    raw_errors = error.errors(include_input=False, include_url=False)
    errors = tuple(_sanitize_error(item) for item in raw_errors)
    branch_counts: dict[int, Counter[str]] = defaultdict(Counter)
    for item in errors:
        if item.component_index is not None and item.branch is not None:
            branch_counts[item.component_index][item.branch] += 1
    literal_failures: Counter[tuple[int, str]] = Counter(
        (item.component_index, item.branch)
        for item in errors
        if item.component_index is not None
        and item.branch is not None
        and item.raw_type == "literal_error"
        and item.location.endswith(".component_type")
    )
    primary_branches = {
        index: min(
            counts,
            key=lambda branch: (
                literal_failures[(index, branch)] > 0,
                counts[branch],
                branch,
            ),
        )
        for index, counts in branch_counts.items()
    }
    categorized: list[tuple[_Error, str]] = []
    for item in errors:
        secondary = (
            item.component_index is not None
            and item.branch is not None
            and primary_branches.get(item.component_index) != item.branch
        )
        category = (
            "union_branch_mismatch"
            if secondary
            else _canonical_error_type(item.raw_type, item.location)
        )
        categorized.append((item, category))
    type_histogram = Counter(category for _, category in categorized)
    location_histogram = Counter(item.location for item, _ in categorized)
    by_location = Counter((item.location, category) for item, category in categorized)
    components = {
        item.component_index for item in errors if item.component_index is not None
    }
    model_validator = sum(item.location == "model_validator" for item in errors)
    duplicate = any(
        item.location == "model_validator" and item.raw_type == "value_error"
        for item in errors
    )
    union_indexes = {
        item.component_index
        for item in errors
        if item.component_index is not None
        and len(branch_counts[item.component_index]) > 1
    }
    primary_categories = [
        category
        for item, category in categorized
        if category != "union_branch_mismatch"
        and item.location not in {"revised_components", "model_validator"}
    ]
    probable = _probable_primary(primary_categories, duplicate)
    shape_counts = Counter(primary_branches.values())
    return SafeDTOValidationDiagnostics(
        total_error_count=len(errors),
        unique_error_category_count=len(type_histogram),
        affected_component_count=len(components),
        top_level_error_count=sum(
            item.location in {"revised_components", "model_validator"}
            for item in errors
        ),
        nested_error_count=sum(item.component_index is not None for item in errors),
        model_validator_error_count=model_validator,
        union_branch_error_count=type_histogram["union_branch_mismatch"],
        error_type_histogram=tuple(sorted(type_histogram.items())),
        location_shape_histogram=tuple(sorted(location_histogram.items())),
        error_category_by_location_shape=tuple(
            sorted(
                (location, category, count)
                for (location, category), count in by_location.items()
            )
        ),
        distinct_location_shape_count=len(location_histogram),
        probable_primary_failure_category=probable,
        union_expansion_suspected=bool(union_indexes),
        duplicate_reference_validator_triggered=duplicate,
        single_component_concentration=len(components) == 1,
        multi_component_distribution=len(components) > 1,
        story_shape_count=shape_counts["story_component"],
        text_shape_count=shape_counts["text_component"],
        cta_shape_count=shape_counts["cta_component"],
        ambiguous_shape_count=sum(
            1
            for counts in branch_counts.values()
            if len({count for count in counts.values()}) == 1
        ),
        unknown_shape_count=max(0, len(components) - len(primary_branches)),
    )


def _sanitize_error(item: dict[str, Any]) -> _Error:
    location = tuple(item.get("loc", ()))
    component_index = next(
        (value for value in location if isinstance(value, int)), None
    )
    branch = next(
        (
            safe
            for token in location
            if isinstance(token, str)
            for internal, safe in _BRANCHES.items()
            if internal in token
        ),
        None,
    )
    return _Error(
        raw_type=str(item.get("type", "unknown")),
        location=_safe_location(location),
        component_index=component_index,
        branch=branch,
    )


def _safe_location(location: tuple[Any, ...]) -> str:
    if not location:
        return "model_validator"
    parts = ["revised_components"] if location[0] == "revised_components" else []
    for token in location[1:]:
        if isinstance(token, int):
            if not parts or parts[-1] != "[*]":
                parts.append("[*]")
            continue
        if any(internal in str(token) for internal in _BRANCHES):
            continue
        field = _FIELDS.get(str(token), "unknown_field")
        parts.append(field)
    if not parts:
        return "unknown_location"
    value = parts[0]
    for part in parts[1:]:
        value += part if part == "[*]" else f".{part}"
    return value


def _canonical_error_type(raw_type: str, location: str) -> str:
    if raw_type == "value_error":
        return (
            "duplicate_component_reference"
            if location == "model_validator"
            else "model_validator_failure"
        )
    return _ERROR_TYPES.get(raw_type, "unknown_validation_error")


def _probable_primary(categories: list[str], duplicate: bool) -> str:
    if duplicate:
        return "duplicate_component_reference"
    priority = (
        ("missing", "missing_required_field"),
        ("extra_forbidden", "extra_field"),
        ("literal_error", "wrong_component_type"),
        ("pattern_mismatch", "invalid_reference_pattern"),
        ("string_type", "invalid_nested_type"),
        ("list_type", "invalid_nested_type"),
        ("model_type", "invalid_component_shape"),
        ("dict_type", "invalid_component_shape"),
        ("string_too_short", "constraint_violation"),
        ("string_too_long", "constraint_violation"),
        ("too_short", "constraint_violation"),
        ("too_long", "constraint_violation"),
        ("model_validator_failure", "invalid_component_shape"),
    )
    return next(
        (result for category, result in priority if category in categories),
        "unresolved",
    )


def _json_pairs(values: tuple[tuple[str, int], ...]) -> str:
    return json.dumps(dict(values), sort_keys=True, separators=(",", ":"))


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
