"""Read-only graph qualification for frozen V5.4 semantic-rule populations.

This module deliberately has no repository or activation I/O.  Callers must
provide a rule-content freeze identity and the already-admitted rule records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Collection, Mapping, Sequence


@dataclass(frozen=True)
class CoverageTargets:
    family_minimum: int = 17
    family_total: int = 21
    anchor_family_minimum: int = 10
    result_family_minimum: int = 10
    terminal_family_minimum: int = 10
    distinct_family_two_edge_minimum: int = 24
    three_stage_minimum: int = 12
    island_fraction_maximum: float = 0.10
    ambiguous_cells_maximum: int = 0
    unreviewed_privileged_maximum: int = 0
    priority_families: tuple[str, ...] = (
        "PHYSICAL_ACTION", "MOVEMENT_LOCATION", "OBSERVATION_PERCEPTION",
        "MEASUREMENT", "MATCHING_VERIFICATION", "RECORDING", "REPRESENTATION",
        "INFORMATION_TRANSFER", "CLASSIFICATION", "STATE_TRANSITION", "TRIGGERING",
        "PROCEDURAL_ACTION", "LOGICAL_IMPLICATION", "TEMPORAL_RELATION", "CAUSAL_RELATION",
    )


@dataclass(frozen=True)
class CoverageReport:
    freeze_identity: str
    rule_count: int
    represented_families: tuple[str, ...]
    anchor_capable_families: tuple[str, ...]
    result_consumable_families: tuple[str, ...]
    terminal_capable_families: tuple[str, ...]
    compatible_edges: tuple[tuple[str, str], ...]
    distinct_family_two_edge_compositions: tuple[tuple[str, str], ...]
    anchor_intermediate_terminal_compositions: tuple[tuple[str, str, str], ...]
    disconnected_island_count: int
    disconnected_rule_island_fraction: float
    ambiguous_rule_cells: tuple[str, ...]
    unreviewed_privileged_affordance_rules: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]
    duplicate_rule_identities: tuple[str, ...]
    duplicate_semantic_rules: tuple[tuple[str, ...], ...]
    contradictions: tuple[tuple[str, ...], ...]
    incompatible_outcome_overlaps: tuple[tuple[str, str], ...]
    checks: Mapping[str, bool]
    qualified: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def qualify_frozen_rules(
    rules: Sequence[Mapping[str, Any]],
    *,
    rule_content_freeze_identity: str,
    privileged_affordances: Collection[str] = (),
    privileged_review_receipts: Mapping[str, str] | None = None,
    targets: CoverageTargets = CoverageTargets(),
) -> CoverageReport:
    """Measure a frozen population without mutating it or granting authority."""
    if not rule_content_freeze_identity.strip():
        raise ValueError("RULE_CONTENT_FREEZE identity is required before qualification")
    receipts = privileged_review_receipts or {}
    indexed = [(str(rule.get("rule_identity", "")), rule) for rule in rules]
    ids = [identity for identity, _ in indexed]

    duplicate_ids = _duplicates(ids)
    semantic_groups = _group_ids(indexed, _semantic_signature)
    duplicate_semantics = tuple(group for group in semantic_groups if len(group) > 1)
    antecedent_groups = _group_records(indexed, _antecedent_signature)
    contradictions = tuple(
        tuple(sorted(identity for identity, _ in group))
        for group in antecedent_groups
        if len({_outcome_signature(rule) for _, rule in group}) > 1
    )

    edges = tuple(
        sorted(
            (left_id, right_id)
            for left_id, left in indexed
            for right_id, right in indexed
            if left_id != right_id and _compatible(left, right)
        )
    )
    by_id = {identity: rule for identity, rule in indexed}
    two_edge = tuple(
        edge
        for edge in edges
        if _family(by_id[edge[0]]) != _family(by_id[edge[1]])
    )
    edge_set = set(edges)
    three_stage = tuple(
        sorted(
            (anchor_id, middle_id, terminal_id)
            for anchor_id, anchor in indexed
            if _position(anchor, "anchor")
            for middle_id, middle in indexed
            if _position(middle, "intermediate") and (anchor_id, middle_id) in edge_set
            for terminal_id, terminal in indexed
            if _position(terminal, "terminal")
            and (middle_id, terminal_id) in edge_set
            and len({anchor_id, middle_id, terminal_id}) == 3
        )
    )

    families = tuple(sorted({_family(rule) for _, rule in indexed}))
    anchors = _families_for_position(indexed, "anchor")
    consumable = tuple(sorted({_family(by_id[left]) for left, _ in edges}))
    terminals = _families_for_position(indexed, "terminal")
    components = _weak_components(ids, edges)
    largest = max((len(component) for component in components), default=0)
    disconnected_count = max(0, len(components) - (1 if components else 0))
    island_fraction = (len(ids) - largest) / len(ids) if ids else 0.0

    cells: dict[str, set[str]] = {}
    for identity, rule in indexed:
        cells.setdefault(str(rule.get("curriculum_cell", "")), set()).add(identity)
    ambiguous = tuple(sorted(cell for cell, members in cells.items() if len(members) > 1))
    privileged = set(privileged_affordances)
    unreviewed = tuple(
        sorted(
            identity
            for identity, rule in indexed
            if _all_affordances(rule) & privileged and not receipts.get(identity, "").strip()
        )
    )
    cycles = _cycles(ids, edges)
    overlaps = _incompatible_overlaps(indexed)

    checks = {
        "predicate_family_coverage": len(families) >= targets.family_minimum,
        "priority_family_coverage": set(targets.priority_families) <= set(families),
        "anchor_family_coverage": len(anchors) >= targets.anchor_family_minimum,
        "result_consumable_family_coverage": len(consumable) >= targets.result_family_minimum,
        "terminal_family_coverage": len(terminals) >= targets.terminal_family_minimum,
        "distinct_family_two_edge_compositions": len(two_edge) >= targets.distinct_family_two_edge_minimum,
        "anchor_intermediate_terminal_compositions": len(three_stage) >= targets.three_stage_minimum,
        "disconnected_rule_island_fraction": island_fraction <= targets.island_fraction_maximum,
        "ambiguous_rule_cells": len(ambiguous) <= targets.ambiguous_cells_maximum,
        "unreviewed_privileged_affordances": len(unreviewed) <= targets.unreviewed_privileged_maximum,
        "acyclic": not cycles,
        "unique_rule_identities": not duplicate_ids,
        "no_duplicate_semantic_rules": not duplicate_semantics,
        "no_contradictions": not contradictions,
        "no_incompatible_outcome_overlap": not overlaps,
    }
    return CoverageReport(
        freeze_identity=rule_content_freeze_identity,
        rule_count=len(rules), represented_families=families,
        anchor_capable_families=anchors, result_consumable_families=consumable,
        terminal_capable_families=terminals, compatible_edges=edges,
        distinct_family_two_edge_compositions=two_edge,
        anchor_intermediate_terminal_compositions=three_stage,
        disconnected_island_count=disconnected_count,
        disconnected_rule_island_fraction=island_fraction,
        ambiguous_rule_cells=ambiguous,
        unreviewed_privileged_affordance_rules=unreviewed, cycles=cycles,
        duplicate_rule_identities=duplicate_ids,
        duplicate_semantic_rules=duplicate_semantics, contradictions=contradictions,
        incompatible_outcome_overlaps=overlaps, checks=checks,
        qualified=all(checks.values()),
    )


def _family(rule: Mapping[str, Any]) -> str:
    return str(rule.get("predicate_family", ""))


def _position(rule: Mapping[str, Any], name: str) -> bool:
    return bool(rule.get("composition", {}).get(name, False))


def _consumable_classes(rule: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(rule.get("composition", {}).get("consumable_result_classes", ()))


def _all_affordances(rule: Mapping[str, Any]) -> set[str]:
    required = rule.get("required_affordances", {})
    return set(required.get("actor", ())) | set(required.get("patient", ())) | set(rule.get("result", {}).get("affordances", ()))


def _compatible(predecessor: Mapping[str, Any], successor: Mapping[str, Any]) -> bool:
    result = predecessor.get("result", {})
    result_class = result.get("class")
    if result_class not in _consumable_classes(successor):
        return False
    result_roles = set(result.get("roles", ()))
    result_affordances = set(result.get("affordances", ()))
    sides = (
        (successor.get("actor_classes", ()), successor.get("actor_roles", ()), successor.get("required_affordances", {}).get("actor", ())),
        (successor.get("patient_classes", ()), successor.get("patient_roles", ()), successor.get("required_affordances", {}).get("patient", ())),
    )
    return any(
        result_class in classes
        and result_roles == set(roles)
        and result_affordances == set(affordances)
        for classes, roles, affordances in sides
    )


def _antecedent_signature(rule: Mapping[str, Any]) -> tuple[Any, ...]:
    required = rule.get("required_affordances", {})
    return (
        _family(rule), tuple(sorted(rule.get("actor_classes", ()))),
        tuple(sorted(rule.get("patient_classes", ()))), tuple(sorted(rule.get("actor_roles", ()))),
        tuple(sorted(rule.get("patient_roles", ()))), tuple(sorted(required.get("actor", ()))),
        tuple(sorted(required.get("patient", ()))), tuple(sorted(rule.get("preconditions", ()))),
        str(rule.get("transition", {}).get("direction", "")),
    )


def _outcome_signature(rule: Mapping[str, Any]) -> tuple[Any, ...]:
    result = rule.get("result", {})
    return (result.get("class"), tuple(sorted(result.get("roles", ()))), tuple(sorted(result.get("affordances", ()))))


def _semantic_signature(rule: Mapping[str, Any]) -> tuple[Any, ...]:
    return _antecedent_signature(rule) + _outcome_signature(rule)


def _overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if _family(left) != _family(right):
        return False
    for key in ("actor_classes", "patient_classes", "actor_roles", "patient_roles"):
        if not set(left.get(key, ())) & set(right.get(key, ())):
            return False
    return bool(set(left.get("preconditions", ())) & set(right.get("preconditions", ())))


def _incompatible_overlaps(indexed: Sequence[tuple[str, Mapping[str, Any]]]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(
        (left_id, right_id)
        for offset, (left_id, left) in enumerate(indexed)
        for right_id, right in indexed[offset + 1:]
        if _overlap(left, right) and _outcome_signature(left) != _outcome_signature(right)
    ))


def _duplicates(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _group_records(indexed: Sequence[tuple[str, Mapping[str, Any]]], key: Any) -> tuple[tuple[tuple[str, Mapping[str, Any]], ...], ...]:
    groups: dict[tuple[Any, ...], list[tuple[str, Mapping[str, Any]]]] = {}
    for item in indexed:
        groups.setdefault(key(item[1]), []).append(item)
    return tuple(tuple(group) for group in groups.values())


def _group_ids(indexed: Sequence[tuple[str, Mapping[str, Any]]], key: Any) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(sorted(identity for identity, _ in group)) for group in _group_records(indexed, key))


def _families_for_position(indexed: Sequence[tuple[str, Mapping[str, Any]]], position: str) -> tuple[str, ...]:
    return tuple(sorted({_family(rule) for _, rule in indexed if _position(rule, position)}))


def _weak_components(ids: Sequence[str], edges: Sequence[tuple[str, str]]) -> tuple[frozenset[str], ...]:
    neighbors = {identity: set() for identity in ids}
    for left, right in edges:
        neighbors[left].add(right); neighbors[right].add(left)
    remaining = set(ids); components = []
    while remaining:
        stack = [next(iter(remaining))]; component = set()
        while stack:
            node = stack.pop()
            if node in component: continue
            component.add(node); stack.extend(neighbors[node] - component)
        remaining -= component; components.append(frozenset(component))
    return tuple(components)


def _cycles(ids: Sequence[str], edges: Sequence[tuple[str, str]]) -> tuple[tuple[str, ...], ...]:
    adjacent = {identity: set() for identity in ids}
    for left, right in edges: adjacent[left].add(right)
    found: set[tuple[str, ...]] = set()
    def visit(start: str, node: str, path: tuple[str, ...]) -> None:
        for nxt in adjacent[node]:
            if nxt == start:
                cycle = path
                rotations = [cycle[i:] + cycle[:i] for i in range(len(cycle))]
                found.add(min(rotations))
            elif nxt not in path:
                visit(start, nxt, path + (nxt,))
    for identity in ids: visit(identity, identity, (identity,))
    return tuple(sorted(found))
