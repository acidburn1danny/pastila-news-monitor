"""Materialize the local, non-consuming editorial Bridge execution gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from project_editor_core_editorial_bridge_arms import projection

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
NAME = "editor-core-editorial-bridge-v1"
PUBLISHED_COMMIT = "94880823ac060539f21b1df4b8374b04a484ad78"
PUBLISHED_TREE = "ff2ec5bcf306e81710c3dd25fff1e9234ef48d6c"
PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
ROOTFS = "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
SNAPSHOT = "f2074e618ba99a03e327ef2462a814b5a9503bbe5994692805ff8c4f11375126"
SOURCE_FILES = (
    "scripts/audit_editor_core_editorial_bridge_token_lengths.py",
    "scripts/run_editor_core_editorial_bridge_token_audit.sh",
    "scripts/project_editor_core_editorial_bridge_arms.py",
    "scripts/validate_editor_core_editorial_bridge_naturalistic.py",
    "scripts/preflight_editor_core_editorial_bridge.py",
    "scripts/audit_editor_core_editorial_bridge_boundary.py",
    "scripts/build_editor_core_editorial_bridge_boundary.py",
    "tests/test_editor_core_editorial_bridge_boundary.py",
    "docs/editor-core-editorial-bridge-execution-gate.md",
    "scripts/launch_editor_core_v10_v12_targeted_r6_zero_step.py",
    "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py",
    "scripts/probe_production_core_isolated_gpu_v15.sh",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def protocol() -> dict:
    operators = ["FACT_SELECTION", "QUALIFIED_COMPRESSION", "CHRONOLOGICAL_ORDER", "PRECISE_ATTRIBUTION",
                 "SUPPORTED_CONTRAST", "FACTUAL_TRANSITION", "NATURAL_ROMANIAN", "EPISTEMIC_GUARD"]
    return {
        "status": "PROTOCOL_FROZEN_CORPUS_NOT_MATERIALIZED",
        "required_cases": 96,
        "operator_quota": {operator: 12 for operator in operators},
        "justification": "Twelve independent source families per operator gives >93% chance to observe a failure mode present in at least 20% of that stratum; 96 total paired cases give >94% chance to observe a 3% overall failure mode, assuming independent draws.",
        "collection_order": "FREEZE_AND_HASH_BEFORE_FIRST_REAL_ABLATION_OR_A0_EVALUATION",
        "source_requirement": "REAL_INDEPENDENT_NATURALISTIC_DOCUMENTS_NOT_GENERATOR_TEMPLATES_OR_FROZEN_HOLDOUTS",
        "source_family_requirement": "96_DISTINCT_SOURCE_DOCUMENT_FAMILIES; provenance URI or project source identity plus acquisition timestamp and SHA256",
        "case_schema": ["case_id", "operator", "source_family", "source_document_sha256", "source_provenance",
                        "request", "authority_spans", "request_identity"],
        "answer_key_schema": ["case_id", "request_identity", "supported_claims", "required_qualifications",
                              "disallowed_inferences", "editorial_operation", "source_span_bindings"],
        "request_key_separation": "REQUESTS_ONLY_IN_INFERENCE; KEYS_ONLY_IN_BLINDED_SCORING; NEITHER_IN_TRAINING",
        "anti_contamination": "EXACT_CASE_SOURCE_TARGET_EXCLUSION_AND_5GRAM_REVIEW_AGAINST_BRIDGE_TRAIN_DEV_HOLDOUT_AND_R2_R6_FROZEN_EVIDENCE",
        "evaluation_design": "PAIRED_R2_VS_ONE_PRESELECTED_CHALLENGER; CANDIDATE_BLINDED; TWO_INDEPENDENT_REVIEWERS; DISAGREEMENTS_INDETERMINATE_PENDING_RESOLUTION",
        "scoring_axes": ["FACTUAL_EPISTEMIC_SAFETY", "EDITORIAL_REWRITE_QUALITY", "ROMANIAN_NATURALNESS", "REGRESSION_PROTECTION"],
        "source_copy": "SAFE_COPY_MAY_PASS_FACTUALITY_BUT_FAIL_REWRITE_WHEN_REQUESTED",
        "use_limit": "ONE_SHOT_PARENT_SELECTION_AFTER_DEVELOPMENT_ARM_RULES_LOCKED; NO_TRAINING_OR_ITERATIVE_TUNING",
    }


def stops() -> dict:
    return {
        "before_any_ablation": ["PUBLISHED_GATE_AND_SOURCE_CLOSURE", "EXACT_TOKENIZER_EOS_AND_3072_CAP",
                                "R2_PARENT_BASE_MODEL_ROOTFS_CUDA_SNAPSHOT_CLOSURE", "NATURALISTIC_CORPUS_FROZEN_AND_SEALED",
                                "SPLIT_ISOLATION", "DISTINCT_EMPTY_EXT4_OUTPUT_PER_RUN"],
        "immediate_program_stop": ["ANY_TRAIN_EVAL_OR_NATURALISTIC_TARGET_LEAKAGE", "RUNTIME_OR_SOURCE_IDENTITY_DRIFT",
                                   "UNBOUND_RETRY_OR_OUTPUT_REUSE", "EVALUATION_BLINDING_FAILURE"],
        "immediate_arm_stop": ["CONFIRMED_MATERIAL_FACTUAL_OR_EPISTEMIC_REGRESSION_ON_DEVELOPMENT",
                               "ARM_PROCESS_OR_CHECKPOINT_FAILURE"],
        "run_failure": "TERMINAL_FOR_THAT_RUN; PRESERVE_EVIDENCE; NO_AUTOMATIC_RETRY",
        "development_rule": "THREE_SEEDS_PER_ARM; PAIRED_BLINDED_CASE_REVIEW; NOMINATE_AT_MOST_ONE_ARM; NO_SAFETY_REGRESSION; EDITORIAL_WINS_MUST_EXCEED_LOSSES_WITH_EXACT_ONE_SIDED_SIGN_TEST_P_LE_0.025",
        "controlled_holdout_rule": "ONE_SHOT_AFTER_ARM_AND_THRESHOLD_LOCK; ZERO_MATERIAL_SAFETY_REGRESSIONS; NO_HOLDOUT_FEEDBACK_TO_TRAINING",
        "naturalistic_selection_rule": "ONE_PRESELECTED_ARM_VS_R2_ON_96_CASES; TWO_INDEPENDENT_BLINDED_REVIEWERS; ZERO_CONFIRMED_MATERIAL_SAFETY_REGRESSIONS; PAIRED_EDITORIAL_SIGN_TEST_P_LE_0.025; NO_SEVERE_ROMANIAN_REGRESSION",
        "source_copy_not_win": True,
        "training_loss_not_parent_selection": True,
        "parent_change_requires_separate_evidence_and_owner_action": True,
        "r3_r6_selected": False,
    }


def build(token_receipt: Path, output: Path) -> dict:
    token = json.loads(token_receipt.read_bytes())
    if (token.get("manifest_identity") != "a4649f59a5a536c688e7d3741bc46e82d8997dc6a8c04948a25424528102ba3a"
            or token.get("plan_identity") != "4caa3811ff1eb9e19bc0e460edd760755e224100953595e5a5c4b91ab73cb6ef"
            or token.get("base_model_identity") != MODEL or token.get("maximum_sequence_tokens", 99999) > 3072
            or token.get("model_loaded") is not False or token.get("optimizer_steps") != 0):
        raise ValueError("token receipt mismatch")
    token_core = {k: v for k, v in token.items() if k != "receipt_identity"}
    if token.get("receipt_identity") != sha(canonical(token_core)):
        raise ValueError("token receipt identity")
    projection_result = projection()
    sources = {name: sha((ROOT / name).read_bytes()) for name in SOURCE_FILES}
    core = {
        "schema": "editor-core-editorial-bridge-execution-boundary", "schema_version": 1,
        "status": "LOCAL_PREFLIGHT_ONLY_NO_ABLATION_AUTHORITY",
        "published_dataset_commit": PUBLISHED_COMMIT, "published_dataset_tree": PUBLISHED_TREE,
        "published_manifest_identity": token["manifest_identity"], "published_plan_identity": token["plan_identity"],
        "parent_adapter_identity": PARENT, "parent_checkpoint_identity": CHECKPOINT,
        "base_model_identity": MODEL, "rootfs_sha256": ROOTFS, "driver_snapshot_manifest_identity": SNAPSHOT,
        "token_audit_receipt_identity": token["receipt_identity"], "token_audit_blob_sha256": sha(token_receipt.read_bytes()),
        "arm_projection_identity": projection_result["projection_identity"],
        "arm_corpus_sha256": {k: v["sha256"] for k, v in projection_result["arms"].items()},
        "naturalistic_evaluation": protocol(), "stop_rules": stops(),
        "source_hashes": sources,
        "training_authorized": False, "training_performed": False, "optimizer_steps": 0,
        "development_parent_changed": False, "adjudication_performed": False, "promotion": False,
    }
    result = {**core, "boundary_identity": sha(canonical(core))}
    output.write_bytes(json.dumps(result, ensure_ascii=False, indent=2).encode() + b"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ART / f"{NAME}-boundary.json")
    args = parser.parse_args()
    value = build(args.token_receipt, args.output)
    print(json.dumps({"boundary_identity": value["boundary_identity"], "source_files": len(value["source_hashes"])}))
