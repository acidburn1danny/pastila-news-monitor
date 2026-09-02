"""Fail-closed, source-blind adjudication checks for V5.4 semantic rules.

This module does not author, admit, activate, or persist rules.  It only produces
an advisory review result for a candidate supplied by a separate RULE_AUTHOR.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence


ADJUDICATOR_IDENTITY = "RULE_ADJUDICATOR_V54_01"

REVIEW_DIMENSIONS = (
    "SEMANTIC_DIRECTION",
    "ACTOR_PATIENT_TYPING",
    "ROLE_BINDING",
    "AFFORDANCE_AUTHORITY",
    "CAUSAL_NECESSITY",
    "COUNTERFACTUAL_DEPENDENCY",
    "CONSEQUENCE_NON_SUBSTITUTABILITY",
    "COMPOSITION_COMPATIBILITY",
    "ADVERSARIAL_OVERBREADTH",
)

_REQUIRED_FIELDS = {
    "schema_version",
    "curriculum_cell",
    "origin",
    "provenance",
    "predicate_family",
    "actor_classes",
    "patient_classes",
    "actor_roles",
    "patient_roles",
    "required_affordances",
    "preconditions",
    "transition",
    "result",
    "counterfactual",
    "non_substitutability",
    "composition",
    "scope",
    "author_identity",
    "adjudication_receipt",
    "rule_identity",
}


@dataclass(frozen=True)
class ReviewEvidence:
    dimension: str
    verdict: str
    rationale: str
    reviewer_identity: str


@dataclass(frozen=True)
class AdjudicationResult:
    adjudicator_identity: str
    verdict: str
    blockers: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS_ADVISORY_REVIEW_ONLY"


def canonical_rule_identity(candidate: Mapping[str, Any]) -> str:
    """Return the contract identity for JSON-compatible V5.4 semantic content.

    Candidate semantic content uses strings, booleans, integers, arrays, and
    objects. Floating-point values are rejected to avoid non-portable number
    serialization at the adjudication boundary.
    """

    payload = {
        key: value
        for key, value in candidate.items()
        if key not in {"rule_identity", "adjudication_receipt"}
    }
    _reject_floats(payload)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def adjudicate_candidate(
    candidate: Mapping[str, Any],
    reviews: Sequence[ReviewEvidence],
    *,
    ontology: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    curriculum: Mapping[str, Any],
    adjudicator_identity: str = ADJUDICATOR_IDENTITY,
) -> AdjudicationResult:
    """Evaluate one authored candidate without granting admission authority."""

    blockers: list[str] = []
    missing = _REQUIRED_FIELDS - candidate.keys()
    extra = candidate.keys() - _REQUIRED_FIELDS
    if missing:
        blockers.append(f"SCHEMA_MISSING_FIELDS:{','.join(sorted(missing))}")
    if extra:
        blockers.append(f"SCHEMA_EXTRA_FIELDS:{','.join(sorted(extra))}")
    if missing:
        return _result(adjudicator_identity, blockers)

    if candidate["schema_version"] != "1.0.0":
        blockers.append("SCHEMA_VERSION_MISMATCH")
    if candidate["origin"] != "FROZEN_GENERIC_ONTOLOGY":
        blockers.append("SOURCE_BLIND_ORIGIN_REQUIRED")
    provenance = candidate.get("provenance", {})
    if provenance.get("created_before_family_access") is not True:
        blockers.append("FAMILY_ACCESS_BOUNDARY_NOT_PROVEN")
    if provenance.get("blind_access") is not False:
        blockers.append("BLIND_ACCESS_BOUNDARY_NOT_PROVEN")
    if candidate["author_identity"] == adjudicator_identity:
        blockers.append("AUTHOR_ADJUDICATOR_IDENTITY_COLLISION")

    families = {item["family"]: item for item in taxonomy.get("families", [])}
    family = families.get(candidate["predicate_family"])
    if family is None:
        blockers.append("UNKNOWN_PREDICATE_FAMILY")
    else:
        _validate_family_shape(candidate, family, ontology, blockers)
        curriculum_families = {
            domain
            for batch in curriculum.get("ordering", [])
            for domain in batch.get("domains", [])
        }
        if candidate["predicate_family"] not in curriculum_families:
            blockers.append("FAMILY_NOT_IN_PRECOMMITTED_CURRICULUM")

    _validate_contract_constants(candidate, blockers)
    try:
        expected_identity = canonical_rule_identity(candidate)
    except (TypeError, ValueError):
        blockers.append("NON_CANONICAL_JSON_VALUE")
    else:
        if candidate["rule_identity"] != expected_identity:
            blockers.append("CANONICAL_IDENTITY_MISMATCH")

    _validate_review_evidence(reviews, candidate["author_identity"], adjudicator_identity, blockers)
    return _result(adjudicator_identity, blockers)


def validate_composition_chain(
    candidates: Sequence[Mapping[str, Any]], *, max_edges: int = 3
) -> tuple[str, ...]:
    """Check a declared linear composition; an empty tuple means no blockers."""

    blockers: list[str] = []
    if not 2 <= len(candidates) <= max_edges:
        blockers.append("CHAIN_EDGE_BUDGET_VIOLATION")
        return tuple(blockers)
    if not candidates[0]["composition"]["anchor"]:
        blockers.append("CHAIN_REQUIRES_ONE_FIRST_ANCHOR")
    if sum(bool(c["composition"]["anchor"]) for c in candidates) != 1:
        blockers.append("CHAIN_ANCHOR_CARDINALITY")
    if sum(bool(c["composition"]["terminal"]) for c in candidates) != 1:
        blockers.append("CHAIN_TERMINAL_CARDINALITY")
    if not candidates[-1]["composition"]["terminal"]:
        blockers.append("CHAIN_TERMINAL_MUST_BE_LAST")
    identities = [c["rule_identity"] for c in candidates]
    if len(set(identities)) != len(identities):
        blockers.append("CYCLIC_OR_REPEATED_RULE_IDENTITY")
    for predecessor, successor in zip(candidates, candidates[1:]):
        result = predecessor["result"]
        consumes = successor["composition"]["consumable_result_classes"]
        if result["class"] not in consumes:
            blockers.append("RESULT_CLASS_MISMATCH")
        if successor["transition"]["predecessor_consumption"] != "REQUIRED":
            blockers.append("IMMEDIATE_PREDECESSOR_NOT_CONSUMED")
    return tuple(dict.fromkeys(blockers))


def _validate_family_shape(candidate, family, ontology, blockers) -> None:
    classes = ontology.get("entity_classes", {})
    actor_classes = candidate["actor_classes"]
    patient_classes = candidate["patient_classes"]
    if not actor_classes or not set(actor_classes) <= set(family["actors"]):
        blockers.append("ACTOR_CLASS_OUTSIDE_FAMILY")
    if not patient_classes or not set(patient_classes) <= set(family["patients"]):
        blockers.append("PATIENT_CLASS_OUTSIDE_FAMILY")
    for kind, bound_classes, roles in (
        ("ACTOR", actor_classes, candidate["actor_roles"]),
        ("PATIENT", patient_classes, candidate["patient_roles"]),
    ):
        if not roles or any(
            role not in classes.get(class_name, {}).get("roles", [])
            for class_name in bound_classes
            for role in roles
        ):
            blockers.append(f"{kind}_ROLE_NOT_AUTHORIZED_BY_CLASS")
    afforded = set(candidate["required_affordances"].get("actor", [])) | set(
        candidate["required_affordances"].get("patient", [])
    )
    if not set(family["requires"]) <= afforded:
        blockers.append("FAMILY_REQUIRED_AFFORDANCE_MISSING")
    positions = set(family["positions"])
    for field, position in (("anchor", "ANCHOR"), ("intermediate", "INTERMEDIATE"), ("terminal", "TERMINAL")):
        if candidate["composition"][field] and position not in positions:
            blockers.append(f"UNAUTHORIZED_{position}_RIGHT")


def _validate_contract_constants(candidate, blockers) -> None:
    if not candidate["preconditions"]:
        blockers.append("EXPLICIT_PRECONDITIONS_REQUIRED")
    if candidate["counterfactual"].get("expected") != "SUCCESSOR_RELATION_BREAKS":
        blockers.append("COUNTERFACTUAL_EXPECTATION_INVALID")
    if candidate["non_substitutability"].get("maximum_compatible_rules") != 1:
        blockers.append("NON_SUBSTITUTABILITY_NOT_EXCLUSIVE")
    if not candidate["scope"].get("domains"):
        blockers.append("SCOPE_DOMAIN_REQUIRED")


def _validate_review_evidence(reviews, author_identity, adjudicator_identity, blockers) -> None:
    by_dimension: dict[str, list[ReviewEvidence]] = {}
    for review in reviews:
        by_dimension.setdefault(review.dimension, []).append(review)
        if review.reviewer_identity == author_identity:
            blockers.append(f"AUTHOR_REVIEW_COLLISION:{review.dimension}")
        if review.verdict != "PASS" or not review.rationale.strip():
            blockers.append(f"REVIEW_NOT_PASSING:{review.dimension}")
    for dimension in REVIEW_DIMENSIONS:
        if len(by_dimension.get(dimension, [])) != 1:
            blockers.append(f"REVIEW_CARDINALITY:{dimension}")
    causal_reviewers = {
        r.reviewer_identity
        for r in reviews
        if r.dimension in {"CAUSAL_NECESSITY", "COUNTERFACTUAL_DEPENDENCY", "CONSEQUENCE_NON_SUBSTITUTABILITY"}
    }
    adversarial_reviewers = {
        r.reviewer_identity for r in reviews if r.dimension == "ADVERSARIAL_OVERBREADTH"
    }
    if not causal_reviewers or causal_reviewers == {adjudicator_identity}:
        blockers.append("INDEPENDENT_CAUSAL_REVIEWER_REQUIRED")
    if not adversarial_reviewers or adversarial_reviewers == {adjudicator_identity}:
        blockers.append("INDEPENDENT_ADVERSARIAL_REVIEWER_REQUIRED")
    if causal_reviewers & adversarial_reviewers:
        blockers.append("CAUSAL_ADVERSARIAL_REVIEWER_COLLISION")


def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise ValueError("floats are outside the V5.4 candidate value domain")
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_floats(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_floats(nested)


def _result(identity: str, blockers: list[str]) -> AdjudicationResult:
    blockers = list(dict.fromkeys(blockers))
    verdict = "BLOCK" if blockers else "PASS_ADVISORY_REVIEW_ONLY"
    return AdjudicationResult(identity, verdict, tuple(blockers))
