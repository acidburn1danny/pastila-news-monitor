"""Deterministic independent review of V5.4 source-blind rule candidates.

This is an adjudication-input review only.  It cannot issue admission receipts,
freeze rule content, activate rules, or calculate population coverage.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping

CAUSAL_REVIEWER = "CAUSAL_REVIEWER_V54_01"
ADVERSARIAL_REVIEWER = "ADVERSARIAL_REVIEWER_V54_01"
PRIVILEGED_FAMILIES = frozenset({"PERMISSION", "AUTHORIZATION", "OBLIGATION", "INSTITUTIONAL_ACTION"})
ABSTRACT_CAUSAL_FAMILIES = frozenset({"CAUSAL_RELATION", "LOGICAL_IMPLICATION"})


def review_catalog(catalog: Mapping[str, Any]) -> dict[str, Any]:
    candidates = catalog.get("candidates", ())
    reviews = [_review_candidate(candidate) for candidate in candidates]
    reasons = Counter(reason for review in reviews for reason in review["reason_codes"])
    evidence = {
        "schema": "V5_4_INDEPENDENT_CAUSAL_ADVERSARIAL_REVIEW_EVIDENCE_V1",
        "status": "REVIEW_COMPLETE_NO_ADMISSION_AUTHORITY",
        "reviewers": {
            "causal": CAUSAL_REVIEWER,
            "adversarial": ADVERSARIAL_REVIEWER,
            "identities_distinct": CAUSAL_REVIEWER != ADVERSARIAL_REVIEWER,
        },
        "authority_limits": {
            "candidate_content_modified": False,
            "rules_admitted": 0,
            "rules_activated": 0,
            "rule_content_frozen": False,
            "coverage_computed": False,
        },
        "review_basis": [
            "V5_4_GENERAL_SEMANTIC_ONTOLOGY_DESIGN_V1",
            "V5_4_GENERAL_PREDICATE_TAXONOMY_V1",
            "V5_4_TRUSTED_SEMANTIC_RULE_CONTRACT_V1",
            "V5_4_RULE_ADMISSION_GOVERNANCE_V1",
            "V5_4_RULE_COMPOSITION_MODEL_V1",
        ],
        "candidate_catalog_schema": catalog.get("schema"),
        "candidate_catalog_identity": canonical_identity(catalog),
        "reviewed_count": len(reviews),
        "approved_for_adjudication_count": sum(r["disposition"] == "APPROVED_FOR_ADJUDICATION" for r in reviews),
        "rejected_count": sum(r["disposition"] == "REJECTED_BEFORE_ADJUDICATION" for r in reviews),
        "reason_counts": dict(sorted(reasons.items())),
        "reviews": reviews,
    }
    evidence["evidence_identity"] = canonical_identity(evidence)
    return evidence


def canonical_identity(value: Mapping[str, Any]) -> str:
    content = {key: item for key, item in value.items() if key != "evidence_identity"}
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _review_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    content = candidate.get("semantic_content", {})
    composition = content.get("composition", {})
    family = content.get("predicate_family", "")
    causal = [
        "COUNTERFACTUAL_NOT_BOUND_TO_CONCRETE_PREDECESSOR_STATE",
        "NON_SUBSTITUTABILITY_ASSERTED_WITHOUT_CONTRAST_EVIDENCE",
    ]
    adversarial = ["TRANSITION_AND_RESULT_MAPPING_UNDER_SPECIFIED"]
    if content.get("transition", {}).get("predecessor_consumption") == "REQUIRED":
        adversarial.append("EXACT_PREDECESSOR_RESULT_SIGNATURE_NOT_DECLARED")
    if composition.get("terminal"):
        adversarial.append("TERMINAL_PREDECESSOR_CONSUMPTION_NOT_EXACTLY_BOUND")
    if family in PRIVILEGED_FAMILIES:
        adversarial.append("PRIVILEGED_AFFORDANCE_SAFETY_NOT_INDEPENDENTLY_ESTABLISHED")
    if family in ABSTRACT_CAUSAL_FAMILIES:
        causal.append("CAUSAL_OR_LOGICAL_LICENSE_ASSUMED_IN_PRECONDITION")
    reasons = causal + adversarial
    return {
        "candidate_identity": candidate.get("candidate_identity"),
        "curriculum_cell": content.get("curriculum_cell"),
        "predicate_family": family,
        "causal_review": "REJECT",
        "adversarial_review": "REJECT",
        "disposition": "REJECTED_BEFORE_ADJUDICATION",
        "reason_codes": reasons,
    }
