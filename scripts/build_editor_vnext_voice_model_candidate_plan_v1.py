"""Build the planning-only VNext VOICE model candidate and acquisition plan."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/artifacts/editor-vnext-voice-model-candidate-plan-v1.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identify(value: dict) -> dict:
    body = {key: item for key, item in value.items() if key != "plan_identity"}
    return {**body, "plan_identity": hashlib.sha256(canonical(body)).hexdigest()}


def build() -> dict:
    invariants = [
        "EDITOR_SETUP_BYTES_IMMUTABLE", "COMMENTARY_SEPARATE", "NO_NEW_FACTUAL_CLAIMS",
        "ABSTENTION_ALLOWED", "NO_SOURCEPACKET_AUTHORITY_FOR_VOICE",
    ]
    return identify({
        "schema": "editor-vnext-voice-model-candidate-acquisition-plan", "schema_version": 1,
        "status": "PASS_PLANNING_ONLY_STOP_BEFORE_ACQUISITION",
        "mechanism_result_identity": "24f78565f1f8bd8c8db65c1d292f1e4162589b3bb154dfd1e76961da5361ee51",
        "hardware": {"gpu": "NVIDIA_RTX_5080", "vram_gib": 16, "platform_tree_identity": "ef5318bfa36af16350ec96d16ef84eb8b55c527894c3c5045f08d4b9ba1bc498"},
        "shortlist_policy": "ONE_EXISTING_ZERO_ACQUISITION_CONTROL_PLUS_TWO_TEXT_ONLY_APACHE_2_CHALLENGERS_ALREADY_BYTE_IDENTIFIED_LOCALLY",
        "candidates": [
            {
                "candidate_id": "V0_R2_MINISTRAL_CONTROL", "role": "ZERO_ACQUISITION_CONTROL",
                "model": "mistralai/Ministral-3-14B-Instruct-2512 plus R2 step-9 adapter",
                "revision": "BOUND_BY_VNEXT_R2_LOCK_53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f",
                "snapshot_bytes": 0, "new_vnext_disk_bytes": 0, "already_in_vnext": True,
                "license_constraint": "EXISTING_VNEXT_R2_DEPLOYMENT_CLOSURE; NO_NEW_LICENSE_DECISION_IN_THIS PLAN",
                "mode": "EXISTING_R2_ADAPTER; COMMENTARY PROMPT ONLY; NO TRAINING",
                "expected_peak_vram_gib": "8_TO_14_ESTIMATE; MUST_MEASURE_AND_NOT_EXCEED_14.5",
                "prior_runtime_seconds_per_editor_case": "10.446568136414_REFERENCE_ONLY_NOT_VOICE_LATENCY",
            },
            {
                "candidate_id": "V1_QWEN3_8B_NON_THINKING", "role": "PRIMARY_CHALLENGER",
                "model": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218",
                "snapshot_identity": "be259728abcc2c864bdf4d035267a8fcf8ccc57e4e277f8bd5d0934f1963fbc7",
                "snapshot_bytes": 16397461266, "new_vnext_disk_bytes": 16397461266,
                "already_in_vnext": False, "available_only_outside_vnext": True,
                "license": "apache-2.0", "mode": "enable_thinking=false",
                "expected_peak_vram_gib": "6_TO_10_ESTIMATE_WITH_FROZEN_NF4; MUST_MEASURE_AND_NOT_EXCEED_14.5",
                "prior_runtime_seconds_per_editor_case": "6.036577845613_REFERENCE_ONLY_NOT_VOICE_LATENCY",
            },
            {
                "candidate_id": "V2_QWEN25_7B_INSTRUCT", "role": "STABLE_TEXT_ONLY_CHALLENGER",
                "model": "Qwen/Qwen2.5-7B-Instruct", "revision": "a09a35458c702b33eeacc393d103063234e8bc28",
                "snapshot_identity": "5fe636f259ab71443c94837b3c19420e0b796c3d9edcd371332b8ff88577e8fd",
                "snapshot_bytes": 15242807270, "new_vnext_disk_bytes": 15242807270,
                "already_in_vnext": False, "available_only_outside_vnext": True,
                "license": "apache-2.0", "mode": "standard instruct",
                "expected_peak_vram_gib": "5_TO_9_ESTIMATE_WITH_FROZEN_NF4; MUST_MEASURE_AND_NOT_EXCEED_14.5",
                "prior_runtime_seconds_per_editor_case": "2.82316664358_REFERENCE_ONLY_NOT_VOICE_LATENCY",
            },
        ],
        "excluded_first_round": [
            {"class": "MULTIMODAL_MODELS", "reason": "No information gain justifies multimodal runtime for text-only VOICE"},
            {"class": "PAID_OR_REMOTE_API", "reason": "Would add secrets, network and recurring dependency"},
            {"class": "NEW_UNFROZEN_MODEL_FAMILIES", "reason": "Adds acquisition and compatibility confounding before known local candidates are tested"},
        ],
        "acquisition": {
            "authorized": False, "download_required_as_first_choice": False,
            "preferred_source": "REVERIFY_AND_COPY_EXISTING_CONTENT_ADDRESSED_LOCAL_SNAPSHOTS_INTO_VNEXT",
            "target_root": "/root/pastila-vnext/v1/components/voice-candidates-v1",
            "aggregate_new_snapshot_bytes": 31640268536,
            "required_free_bytes_for_atomic_two_candidate_materialization": 74017955312,
            "requirements": ["NO_HARDLINK", "NO_SYMLINK_TO_LEGACY", "ALL_BLOB_SHA256_REVERIFIED", "ATOMIC_RENAME_AFTER_COMPLETE_VERIFICATION", "SINGLE_DEPENDENCY_LOCK", "CLEAN_RESTORE_WITH_LEGACY_UNAVAILABLE"],
            "fallback_if_local_bytes_fail_verification": "STOP_AND_REQUEST_SEPARATE_EXACT_REVISION_DOWNLOAD_AUTHORITY",
        },
        "runtime": {
            "quantization": {"backend": "bitsandbytes", "bits": 4, "quant_type": "nf4", "compute_dtype": "bfloat16", "double_quant": True, "persist_quantized_weights": False},
            "versions": {"accelerate": "1.14.0", "bitsandbytes": "0.50.1", "torch": "2.13.0+cu130", "transformers": "5.15.0"},
            "hard_gates": {"peak_vram_gib_max": 14.5, "oom_allowed": False, "model_load_failure_allowed": False, "seconds_per_case_max": 30, "setup_mutations_allowed": 0},
        },
        "contracts": {
            "input": {"schema": "editor-vnext-voice-input", "authority": "EditorSetupPacket only", "fields": ["editor_setup_packet_identity", "factual_setup", "factual_setup_sha256", "bounded_voice_instruction", "optional_repetition_hints"]},
            "output": {"fields": ["commentary", "abstained", "candidate_receipt"], "factual_setup_field_forbidden": True, "structured_json_required": True},
            "factual_invariants": invariants,
        },
        "bakeoff": {
            "authorized": False, "cases": 24, "case_source": "NEW_VNEXT_DEVELOPMENT_SOURCEPACKETS_FROZEN_BEFORE_INFERENCE", "historical_holdouts": False,
            "common_seeds": [161803, 271828, 314159], "outputs": 216,
            "same_prompt_and_decoding": True, "blind_randomization": "PER_CASE_PER_SEED", "answer_key_excluded_from_inference": True,
            "scoring": {
                "hard_safety": ["setup bytes unchanged", "no unsupported actor/event/number/date/status/attribution", "commentary remains separate", "valid abstention"],
                "quality": ["Romanian naturalness", "relevance", "wit", "Pastila Acida voice", "non-generic commentary", "restraint and target appropriateness"],
                "repetition": ["exact duplicate rate", "normalized phrase reuse", "cross-case template reuse", "human perceived repetitiveness"],
                "runtime": ["load seconds", "generation seconds", "peak VRAM", "output tokens", "structural failure rate"],
            },
            "human_review": "BLIND; CASE-LEVEL AGGREGATION BEFORE MODEL UNSEALING; SEEDS RETAINED SEPARATELY",
        },
        "terminal_rules": {
            "STOP": ["any setup mutation", "any unsupported concrete factual claim", "identity drift", "peak VRAM above 14.5 GiB", "OOM", "license or clean-room closure failure"],
            "REVISE": ["structural failure above 2 percent", "abstention above 20 percent", "material repetition cluster", "quality advantage not replicated across at least two seeds", "latency above 30 seconds per case"],
            "CONTINUE": ["zero factual drift", "zero setup mutation", "all dependency and clean-room gates pass", "case-level one-sided exact sign test p<0.05 versus R2", "at least 15 wins and at most 5 losses versus R2", "quality effect replicated across at least two seeds", "no material repetition regression"],
            "authority": "DEVELOPMENT_RESEARCH_ONLY; NO AUTOMATIC PRODUCTION PROMOTION",
        },
        "local_dependency_state": {
            "R2": "IN_VNEXT_ACTIVE_CLOSURE",
            "QWEN3_8B": "LOCAL_OUTSIDE_VNEXT_LEGACY_STORE_NOT_AN_ALLOWED_RUNTIME_DEPENDENCY",
            "QWEN25_7B": "LOCAL_OUTSIDE_VNEXT_LEGACY_STORE_NOT_AN_ALLOWED_RUNTIME_DEPENDENCY",
        },
        "product_root_modified": False, "product_lock_modified": False,
        "model_downloaded": False, "model_loaded": False, "inference_performed": False,
        "training_performed": False, "legacy_dependency_count": 0,
        "next_action_requires_owner_authority": True,
    })


def main() -> None:
    value = build()
    RESULT.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps({"status": value["status"], "plan_identity": value["plan_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
