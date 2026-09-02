"""Source-blind validation for semantic-authority selection precommitments.

The validator accepts metadata envelopes only.  It neither enumerates source
content nor performs selection, scope construction, or basis extraction.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_identity(value: Mapping[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def validate_selection_precommitment(value: Mapping[str, Any]) -> None:
    """Reject governance that leaves a V2-shaped choice after commitment."""
    required = {
        "governance_identity",
        "source_population_frame_policy",
        "selection_precommitment_model",
        "scope_policy",
        "basis_extraction_policy",
        "trust_domain_isolation",
        "forbidden_information",
    }
    if required - value.keys():
        raise ValueError("incomplete selection precommitment")
    if value["governance_identity"] != canonical_identity(
        value, "governance_identity"
    ):
        raise ValueError("precommitment identity mismatch")

    frame = value["source_population_frame_policy"]
    selection = value["selection_precommitment_model"]
    scope = value["scope_policy"]
    extraction = value["basis_extraction_policy"]
    domains = value["trust_domain_isolation"]

    if frame.get("enumeration_frozen_before_entropy") is not True:
        raise ValueError("sampling frame not frozen before entropy")
    if frame.get("inclusion_exclusion_rules_precommitted") is not True:
        raise ValueError("frame criteria not precommitted")
    if frame.get("negative_space_inventory_required") is not True:
        raise ValueError("frame negative-space evidence missing")
    if frame.get("post_freeze_edits") != "NEW_VERSION_NEW_SELECTION_EVENT":
        raise ValueError("mutable sampling frame")

    if selection.get("algorithm") != "CANONICAL_ORDER_PLUS_PUBLIC_ENTROPY_REJECTION_SAMPLING":
        raise ValueError("selection algorithm not objective")
    if selection.get("entropy_source_controlled_by_project") is not False:
        raise ValueError("project-controlled selection entropy")
    if selection.get("single_draw_no_resampling") is not True:
        raise ValueError("resampling permitted")
    if selection.get("selection_before_semantic_inspection") is not True:
        raise ValueError("semantic inspection precedes selection")
    if selection.get("empty_or_invalid_draw") != "FAIL_CLOSED_NO_REDRAW":
        raise ValueError("post-selection redraw path")

    if scope.get("frozen_before_source_selection") is not True:
        raise ValueError("scope can be shaped after source selection")
    if scope.get("semantic_coverage_dependent") is not False:
        raise ValueError("coverage-dependent scope")
    if scope.get("default") != "ENTIRE_SELECTED_SOURCE":
        raise ValueError("selective source scope")
    if scope.get("exceptions") != "PRECOMMITTED_NONSEMANTIC_RULES_ONLY":
        raise ValueError("scope exception loophole")

    if extraction.get("frozen_before_frame_semantic_observation") is not True:
        raise ValueError("extraction policy not precommitted")
    if extraction.get("mode") != "EXHAUSTIVE_ALL_ELIGIBLE_ASSERTIONS":
        raise ValueError("cherry-pickable extraction")
    if extraction.get("ordering") != "SOURCE_BYTE_ORDER":
        raise ValueError("coverage-shaped extraction ordering")
    if extraction.get("stopping_rule") != "END_OF_FROZEN_SCOPE":
        raise ValueError("gaming-prone extraction stop")
    if extraction.get("deduplication") != "RETAIN_FIRST_AND_LOG_EVERY_DUPLICATE":
        raise ValueError("opaque deduplication")
    if extraction.get("coverage_or_relation_class_filter") is not False:
        raise ValueError("V2-shaped extraction filter")

    mandatory = {
        domains.get("frame_registrar"),
        domains.get("entropy_authority"),
        domains.get("selection_executor"),
        domains.get("scope_policy_owner"),
        domains.get("basis_extractor"),
        domains.get("admission_verifier"),
        domains.get("candidate_author"),
        domains.get("rule_adjudicator"),
    }
    if None in mandatory or len(mandatory) != 8:
        raise ValueError("trust-domain separation not demonstrated")
    if domains.get("project_owner") in mandatory:
        raise ValueError("V2-informed owner occupies isolated execution role")
    if domains.get("credential_evidence_required") is not True:
        raise ValueError("identity-label-only separation")

    forbidden = set(value["forbidden_information"])
    needed = {
        "ONTOLOGY_V2",
        "CONTRACT_OR_SCHEMA_V2",
        "CURRICULUM_V2_BATCHES_OR_COVERAGE",
        "HISTORICAL_FAILURES_OR_CANDIDATES",
        "FUTURE_FAMILY_OR_MECHANISM_INFORMATION",
    }
    if not needed <= forbidden:
        raise ValueError("incomplete epistemic exclusion boundary")


def validate_selection_record(
    record: Mapping[str, Any], *, precommitment_identity: str
) -> None:
    """Validate future execution evidence without selecting any source here."""
    if record.get("record_identity") != canonical_identity(record, "record_identity"):
        raise ValueError("selection record identity mismatch")
    if record.get("precommitment_identity") != precommitment_identity:
        raise ValueError("selection/precommitment binding mismatch")
    if record.get("frame_frozen_before_entropy") is not True:
        raise ValueError("frame/entropy ordering violation")
    if record.get("draw_count") != 1 or record.get("resampling") is not False:
        raise ValueError("selection resampling")
    if record.get("complete_negative_space_evidence") is not True:
        raise ValueError("selection negative-space evidence incomplete")
    if record.get("semantic_content_observed_before_selection") is not False:
        raise ValueError("preselection semantic observation")
    if record.get("source_acquired") is not False:
        raise ValueError("pre-source validation record acquired content")
