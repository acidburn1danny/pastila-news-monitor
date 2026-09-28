"""Build the design-only VNext VOICE mechanism selection diagnostic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/artifacts/editor-vnext-voice-mechanism-selection-diagnostic-v1.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identify(value: dict) -> dict:
    body = {key: item for key, item in value.items() if key != "result_identity"}
    return {**body, "result_identity": hashlib.sha256(canonical(body)).hexdigest()}


def build() -> dict:
    common = {
        "input_contract": "EditorSetupPacket",
        "factual_setup_mutation_allowed": False,
        "new_factual_claims_allowed": False,
        "legacy_dependency_count_required": 0,
    }
    return identify({
        "schema": "editor-vnext-voice-mechanism-selection-diagnostic",
        "schema_version": 1,
        "status": "PASS_DESIGN_DIAGNOSTIC",
        "scope": "DESIGN_FIXTURES_ONLY_NO_RUNTIME_MATERIALIZATION",
        "product_contract": common,
        "legacy_inventory": {
            "executor": "MODEL_FREE_DETERMINISTIC",
            "production_activation": "BOUNDED_ALLOWLIST",
            "required_state": [
                "VoiceFactAtomBundle", "semantic_draft_revision", "event_authority",
                "program_eligibility", "owner_selection_receipt", "repetition_snapshot",
                "activation_policy", "governed_context",
            ],
            "general_editor_setup_input_supported": False,
            "proof_fixtures_are_generalization_evidence": False,
        },
        "options": {
            "A_CLEAN_DETERMINISTIC_SUBSET": {
                **common,
                "reusable_principles": [
                    "SEPARATE_FACTUAL_SETUP_AND_COMMENTARY", "DETERMINISTIC_RENDER_INTEGRITY",
                    "SAFE_ABSTENTION", "REPETITION_CONTROL_AS_OPTIONAL_PRODUCT_STATE",
                ],
                "reusable_implementation_without_legacy_state": [],
                "commentary_generalization_demonstrated": False,
                "blocking_reason": "Useful selection and realization depend on factual role bindings and governed legacy state; removing them leaves only fixed generic surfaces or fixture reproduction.",
                "runtime_complexity": "HIGH_IF_MIGRATED; LOW_BUT_NOT_USEFUL_IF_REDUCED_TO_GENERIC_TEMPLATES",
                "persistent_state": "LEGACY_REPETITION_AND_GOVERNANCE_STATE_IF_BEHAVIOR_IS_PRESERVED",
                "clean_room_feasible_under_vnext_invariants": False,
                "verdict": "STOP_AS_VNEXT_GENERAL_VOICE_MECHANISM",
            },
            "B_MODEL_BASED_CREATIVE_REALIZER": {
                **common,
                "minimal_design": {
                    "input": ["immutable factual_setup", "bounded voice instruction", "optional repetition hints"],
                    "output": ["commentary_only", "model_receipt"],
                    "postcondition": "factual_setup is carried separately and byte-identically; commentary cannot replace it",
                },
                "dependency_class": ["CONTENT_ADDRESSED_LOCAL_MODEL", "TOKENIZER", "RUNTIME_LOCK", "DECODING_CONFIG"],
                "commentary_generalization_expected": "PLAUSIBLE_NOT_YET_DEMONSTRATED",
                "available_evidence": ["Legacy product requires creative commentary", "Fixed deterministic proofs do not establish open-domain generalization"],
                "missing_evidence": [
                    "candidate model shortlist", "dependency acquisition closure", "blind commentary quality review",
                    "factual-drift evaluation", "repetition behavior", "runtime and disk feasibility",
                ],
                "runtime_complexity": "MODERATE_AND_EXPLICIT",
                "persistent_state": "MODEL_CLOSURE_PLUS_OPTIONAL_MINIMAL_REPETITION_MEMORY",
                "clean_room_feasible_under_vnext_invariants": "YES_IF_DEPENDENCY_CLOSURE_PASSES",
                "verdict": "BEST_TARGET_MECHANISM_REQUIRES_SEPARATE_OWNER_AUTHORITY",
            },
            "C_VOICE_OUTSIDE_VNEXT_TEMPORARILY": {
                **common,
                "commentary_generalization_demonstrated": "NOT_APPLICABLE",
                "runtime_complexity": "ZERO_INSIDE_VNEXT",
                "persistent_state": "NONE_INSIDE_VNEXT",
                "clean_room_feasible_under_vnext_invariants": True,
                "implication": "VNext factual path can continue as a development closure, but integrated product and global migration cannot pass.",
                "verdict": "CONTINUE_AS_INTERIM_STATE_ONLY",
            },
        },
        "fixtures": [
            {
                "case_id": "NEW_EVENT_OUTSIDE_LEGACY_ALLOWLIST",
                "demonstrates": "Proof and allowlist reproduction do not imply open-domain commentary capability",
                "A_expected": "UNSUPPORTED_WITHOUT_REINTRODUCING_GOVERNED_FACT_STATE",
                "B_required": "COMMENTARY_ONLY_WITH_SETUP_BYTES_UNCHANGED",
            },
            {
                "case_id": "FACTUAL_SETUP_TAMPER_ATTEMPT",
                "demonstrates": "Every future mechanism must keep setup and commentary in separate fields",
                "all_options_required": "REJECT_MUTATED_SETUP",
            },
            {
                "case_id": "NO_SAFE_OR_USEFUL_COMMENTARY",
                "demonstrates": "Abstention is valid and must not alter the factual setup",
                "all_options_required": "SAFE_ABSTENTION",
            },
        ],
        "factual_invariants": [
            "EDITOR_SETUP_BYTES_IMMUTABLE", "COMMENTARY_SEPARATE", "NO_NEW_FACTUAL_CLAIMS",
            "ABSTENTION_ALLOWED", "SOURCEPACKET_AND_R2_RECEIPT_BINDING_PRESERVED",
        ],
        "decision": {
            "best_recommended_target": "B_MODEL_BASED_CREATIVE_REALIZER",
            "current_operational_state": "C_VOICE_OUTSIDE_VNEXT_TEMPORARILY",
            "A_closed_in_tested_form": True,
            "voice_runtime_materialization_authorized": False,
            "next_gate": "OWNER_AUTHORIZED_MODEL_CANDIDATE_AND_ACQUISITION_PLAN",
        },
        "product_root_modified": False,
        "product_lock_modified": False,
        "legacy_dependency_count": 0,
    })


def main() -> None:
    result = build()
    RESULT.write_bytes(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps({"status": result["status"], "result_identity": result["result_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
