"""Source-only Pilot 07 Voice-template root cause and Governance V4 remediation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
DISPOSITION_COMMIT = "ca6eb9823404a0e31ec7d5ead76da93f721d6b1d"
MARKER = "Într-o continuare imaginară"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{DISPOSITION_COMMIT}:{path}"], cwd=ROOT)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write_json(name: str, value: dict[str, Any]) -> None:
    path = ARTIFACTS / name
    require(not path.exists(), f"artifact already exists: {name}")
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == DISPOSITION_COMMIT, "HEAD differs from the authorized disposition commit")
    disposition = git_json(
        "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-voice-rejection-disposition-v1.json"
    )
    voice = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-voice-review-v1.json")
    voice_receipt = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-voice-receipt-v1.json")
    prior = git_json("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    constructor_source = git_bytes("src/pastila_scout/humor_batch2_development_constructor_v1.py").decode("utf-8")
    candidate_paths = {
        "PILOT05": "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-v1.txt",
        "PILOT06": "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-v1.txt",
        "PILOT07": "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt",
    }
    marker_presence = {
        pilot: MARKER in git_bytes(path).decode("utf-8") for pilot, path in candidate_paths.items()
    }
    require(disposition["disposition_identity"] == "4822ba1eede928571f96cb44a70ba5805b24c2707e5153e6747f954bbf7f90ac", "disposition")
    require(voice["voice_review_identity"] == "e15a9b8168362bbc3573744592e31112a165fa60bd45e33b1fe3cba541db5168", "Voice review")
    require(voice_receipt["voice_receipt_identity"] == "3e5f4a580f95c9eab44928e3677ad9e62e50348c0eb60a542d0844b8c3e0a467", "Voice receipt")
    require(all(marker_presence.values()), "cross-pilot marker evidence")
    require(constructor_source.count(MARKER) >= 3, "constructor literal evidence")
    require("constructor_facing_packet_identity" in constructor_source and "source.get(\"sha256\")" in constructor_source, "identity-routed constructor evidence")

    analysis_core = {
        "schema_name": "batch2-pilot07-cross-pilot-voice-template-root-cause-analysis-v1",
        "schema_version": "1.0.0",
        "disposition_commit": DISPOSITION_COMMIT,
        "disposition_identity": disposition["disposition_identity"],
        "candidate_identity": disposition["candidate_identity"],
        "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"],
        "candidate_modified": False,
        "stable_rejection_reason": "CANNED_CROSS_PILOT_CREATIVE_TRANSITION_REUSE",
        "exact_fragment_evidence": {
            "fragment_sha256": hashlib.sha256(MARKER.encode("utf-8")).hexdigest(),
            "fragment_plaintext_in_analysis": False,
            "development_candidate_presence": marker_presence,
            "distinct_candidate_family_count": 3,
        },
        "constructor_source_evidence": {
            "implementation": "pastila_scout.humor_batch2_development_constructor_v1",
            "literal_occurrence_count_at_least": 3,
            "packet_or_source_identity_routing_present": True,
            "historical_behavior_modified": False,
        },
        "root_causes": [
            "V3_PROHIBITED_FIXED_OBLIGATION_WORDING_BUT_DID_NOT_CONSTRAIN_CONSTRUCTOR_SOURCE_LITERALS",
            "V1_CONSTRUCTOR_ROUTED_BY_PACKET_OR_SOURCE_IDENTITY_AND_EMBEDDED_COMPLETE_FAMILY_SPECIFIC_SURFACES",
            "G02B_VERIFIED_VISIBLE_PACKET_ISOLATION_BUT_NOT_STATIC_CONSTRUCTOR_TEMPLATE_DIVERSITY",
            "POST_CONSTRUCTION_G02B_RECONCILED_EXPOSURE_BUT_LACKED_CROSS_PILOT_EXACT_FRAGMENT_COLLISION_CHECK",
            "G03C_CANDIDATE_LOCAL_SHORTCUT_TEST_DID_NOT_COMPARE_NONBLIND_DEVELOPMENT_CONSTRUCTION_FRAGMENTS",
            "G04A_CORRECTLY_TREATED_THE_MARKER_AS_NATURALNESS_NONMATERIAL_BUT_VOICE_REUSE_MATERIALITY_REQUIRES_A_SEPARATE_POOL_AWARE_CHECK",
        ],
        "responsibility": {
            "constructor_implementation_boundary": "PRIMARY",
            "preconstruction_g02b_governance": "CONTRIBUTING",
            "postconstruction_template_collision_governance": "CONTRIBUTING",
            "candidate_local_g03c_scope": "CONTRIBUTING",
            "source_family": "NOT_CAUSAL",
            "selected_proposition": "NOT_CAUSAL",
            "factual_authority": "NOT_CAUSAL",
            "g04a_naturalness_review": "VALID_SEPARATE_JUDGMENT_NOT_CAUSAL",
            "voice_review": "VALID_DETECTION_NOT_CAUSAL",
        },
        "verdict": "ROOT_CAUSE_CONFIRMED_AT_CONSTRUCTOR_TEMPLATE_AND_CROSS_PILOT_COLLISION_GOVERNANCE_BOUNDARY",
    }
    analysis = {
        **analysis_core,
        "analysis_identity": seal("B2_PILOT07_CROSS_PILOT_VOICE_TEMPLATE_ROOT_CAUSE_ANALYSIS_V1", analysis_core),
    }

    governance_core = {
        "schema_name": "batch2-template-diverse-creative-marking-governance-v4",
        "schema_version": "4.0.0",
        "family_version": "TEMPLATE_DIVERSE_CREATIVE_MARKING_V4",
        "supersedes_governance_identity": prior["governance_identity"],
        "preserves_v3_causal_spine_requirements": True,
        "root_cause_analysis_identity": analysis["analysis_identity"],
        "constructor_boundary": {
            "historical_v1_status": "HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_CONSTRUCTOR_RELEASE",
            "new_family_release_requires_separately_frozen_implementation_identity": True,
            "implementation_must_not_route_surface_text_by_source_packet_pilot_or_candidate_identity": True,
            "implementation_must_not_embed_complete_candidate_surfaces_or_reusable_creative_markers": True,
            "implementation_static_audit_required_before_g02b_release": True,
            "historical_v1_behavior_must_remain_byte_exact": True,
        },
        "metadata_first_requirements": [
            "SOURCE_AND_PARTITION_FIXED_BEFORE_ANY_ASSIGNMENT",
            "NO_SOURCE_SELECTION_BY_CREATIVE_MARKER_OR_SURFACE_TEMPLATE",
            "CONSTRUCTION_REVISION_FAMILY_IDENTITY_ASSIGNED_AND_SEALED_BEFORE_RELEASE",
            "NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_IDENTITY_FROZEN_WITHOUT_BLIND_RESERVE_ACCESS",
        ],
        "g02b_preconstruction_requirements": [
            "CONSTRUCTOR_IMPLEMENTATION_NOT_HISTORICAL_V1",
            "CONSTRUCTOR_IMPLEMENTATION_IDENTITY_EXACTLY_BOUND",
            "STATIC_SCAN_NO_IDENTITY_ROUTED_SURFACE_BRANCHES",
            "STATIC_SCAN_NO_COMPLETE_CANDIDATE_SURFACE_LITERALS",
            "STATIC_SCAN_NO_REUSABLE_CREATIVE_MARKER_LITERAL",
            "PACKET_CONTAINS_NO_PLAINTEXT_HISTORICAL_SURFACE_OR_BLIND_METADATA",
            "NO_FIXED_CREATIVE_MARKER_OR_SENTENCE_TEMPLATE_REQUIRED_BY_OBLIGATION",
        ],
        "construction_requirements": [
            "NONFACTUAL_SCOPE_MUST_BE_CLEAR_WITHOUT_A_GLOBALLY_FIXED_PHRASE",
            "CREATIVE_MARKING_MUST_BE_CONTEXT_INTEGRATED_AND_FAMILY_SPECIFIC",
            "CREATIVE_MARKING_CHOICE_MUST_NOT_ENCODE_MECHANISM_LABEL_OR_TARGET_ANSWER",
            "ONE_ATTEMPT_REMAINS_ONE_ATTEMPT_AND_COLLISION_FAILURE_IS_NOT_REPAIR_AUTHORITY",
        ],
        "postconstruction_requirements_before_g02": [
            "EXACT_FRAGMENT_AND_NORMALIZED_NGRAM_COLLISION_CHECK_AGAINST_NONBLIND_DEVELOPMENT_DENYSET",
            "CONSTRUCTION_REVISION_AND_CREATIVE_MARKER_FAMILY_IDENTITIES_DERIVED",
            "COLLISION_FAILS_CLOSED_AS_NONPOSITIVE_WITHOUT_REWRITE_RETRY_OR_SELECTION",
            "NO_BLIND_EVALUATION_CONTENT_METADATA_OR_FINGERPRINTS_ACCESSED",
        ],
        "g03c_additional_requirements": [
            "CANDIDATE_LOCAL_NONSEMANTIC_CUE_AUDIT",
            "CROSS_PILOT_NONBLIND_FRAGMENT_REUSE_AUDIT",
            "CONSTRUCTION_REVISION_FAMILY_PREDICTABILITY_AUDIT",
            "CREATIVE_MARKER_FAMILY_PREDICTABILITY_AUDIT",
            "POOL_STATUS_REMAINS_SEPARATE_FROM_CANDIDATE_PASS",
        ],
        "g04a_voice_separation": {
            "romanian_naturalness_may_pass_a_LOCALLY_NATURAL_MARKER": True,
            "voice_must_reject_MATERIAL_CROSS_FAMILY_TEMPLATE_REUSE": True,
            "one_gate_must_not_silently_override_the_other": True,
        },
        "construction_authority": False,
        "source_acquisition_authority": False,
        "model_exposure_authority": False,
        "training_authority": False,
        "runtime_authority": False,
        "production_authority": False,
    }
    governance = {
        **governance_core,
        "governance_identity": seal("B2_TEMPLATE_DIVERSE_CREATIVE_MARKING_GOVERNANCE_V4", governance_core),
    }

    schema_core = {
        "schema_name": "batch2-template-diverse-creative-marking-conformance-schema-v4",
        "schema_version": "4.0.0",
        "governance_identity": governance["governance_identity"],
        "required_preconstruction_predicates": governance["g02b_preconstruction_requirements"],
        "required_postconstruction_predicates": governance["postconstruction_requirements_before_g02"],
        "required_g03c_predicates": governance["g03c_additional_requirements"],
        "fragment_collision_scope": {
            "eligible_corpus": "NONBLIND_DEVELOPMENT_ONLY",
            "blind_reserve": "PROHIBITED",
            "exact_fragment_minimum": "MULTIWORD_CREATIVE_TRANSITION",
            "normalized_ngram_check": True,
            "semantic_similarity_generation_or_model_use": False,
        },
        "allowed_verdicts": [
            "PASS",
            "FAIL_HISTORICAL_CONSTRUCTOR_V1",
            "FAIL_IDENTITY_ROUTED_SURFACE_BRANCH",
            "FAIL_EMBEDDED_SURFACE_OR_MARKER_LITERAL",
            "FAIL_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION",
            "FAIL_CONSTRUCTION_FAMILY_PREDICTABILITY",
        ],
        "candidate_repair_or_retry_authority": False,
        "candidate_surface_creation_authority": False,
    }
    schema = {
        **schema_core,
        "schema_identity": seal("B2_TEMPLATE_DIVERSE_CREATIVE_MARKING_CONFORMANCE_SCHEMA_V4", schema_core),
    }

    regression_core = {
        "schema_name": "batch2-pilot07-cross-pilot-voice-template-regression-v1",
        "schema_version": "1.0.0",
        "candidate_identity": disposition["candidate_identity"],
        "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"],
        "candidate_bytes_embedded": False,
        "candidate_modified": False,
        "historical_constructor_modified": False,
        "expected_predicates": {
            "ROMANIAN_NATURALNESS_MAY_PASS": True,
            "EXACT_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION_ABSENT": False,
            "CONSTRUCTOR_V1_ELIGIBLE_FOR_FUTURE_RELEASE": False,
            "VOICE_TEMPLATE_REUSE_ABSENT": False,
        },
        "expected_verdict": "FAIL_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION",
        "positive_pool_eligibility": False,
    }
    regression = {
        **regression_core,
        "regression_identity": seal("B2_PILOT07_CROSS_PILOT_VOICE_TEMPLATE_REGRESSION_V1", regression_core),
    }

    visible = canonical({
        "metadata_first_requirements": governance_core["metadata_first_requirements"],
        "construction_requirements": governance_core["construction_requirements"],
    })
    forbidden = [
        rb"HMCV1",
        rb"M13",
        rb"ABSURD_LOGICAL_EXTENSION",
        rb"Absurd Logical Extension",
        rb"mechanism_id",
        rb"mechanism_name",
        rb"Pilot 07",
        MARKER.encode("utf-8"),
    ]
    leakage_hits = [pattern.decode("utf-8") for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not leakage_hits, f"constructor-visible governance leakage: {leakage_hits}")
    audit_core = {
        "schema_name": "batch2-template-diverse-creative-marking-governance-v4-audit-v1",
        "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"],
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "regression_identity": regression["regression_identity"],
        "constructor_visible_label_or_taxonomy_leakage": "PASS_ZERO_HITS",
        "historical_surface_or_marker_leakage_to_future_packet": "PASS_PROHIBITED",
        "blind_reserve_contamination": "PASS_NO_ACCESS",
        "constructor_v1_future_release": "PASS_FAIL_CLOSED_HISTORICAL_ONLY",
        "identity_routed_surface_branching": "PASS_PROHIBITED_AND_PREFLIGHT_REQUIRED",
        "cross_pilot_fragment_collision": "PASS_REQUIRED_BEFORE_G02",
        "naturalness_voice_gate_conflation": "PASS_SEPARATE_NONOVERRIDING_VERDICTS",
        "candidate_or_source_created": False,
        "candidate_or_historical_constructor_modified": False,
        "hidden_construction_or_acquisition_authority": "ABSENT",
        "pilot07_regression": "PASS_EXPECTED_REJECTION",
        "deterministic_blockers_remaining": [],
        "verdict": "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION",
    }
    audit = {
        **audit_core,
        "audit_identity": seal("B2_TEMPLATE_DIVERSE_CREATIVE_MARKING_GOVERNANCE_V4_AUDIT_V1", audit_core),
    }

    write_json("humor-mechanics-batch2-pilot07-cross-pilot-voice-template-root-cause-analysis-v1.json", analysis)
    write_json("humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json", governance)
    write_json("humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json", schema)
    write_json("humor-mechanics-batch2-pilot07-cross-pilot-voice-template-regression-v1.json", regression)
    write_json("humor-mechanics-batch2-template-diverse-creative-marking-governance-v4-audit-v1.json", audit)
    print(json.dumps({
        "verdict": analysis["verdict"],
        "analysis_identity": analysis["analysis_identity"],
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "regression_identity": regression["regression_identity"],
        "audit_identity": audit["audit_identity"],
        "audit_verdict": audit["verdict"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
