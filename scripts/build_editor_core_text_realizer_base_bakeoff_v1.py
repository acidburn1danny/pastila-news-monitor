"""Build the fixture-only EDITOR text-realizer base-model bake-off v1."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-text-realizer-base-bakeoff-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identified(value: dict, key: str) -> dict:
    return {**value, key: sha(canonical(value))}


def write(name: str, value: dict) -> None:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (ART / name).write_bytes(payload)


candidates = identified({
    "schema": "editor-text-realizer-base-bakeoff-candidates", "schema_version": 1,
    "initial_arms": [
        {"arm_id": "C0_R2_MINISTRAL", "role": "CONTROL", "family": "MINISTRAL_3", "architecture_scope": "MULTIMODAL_EXISTING_CONTROL",
         "model": "mistralai/Ministral-3-14B-Instruct-2512", "model_revision": "BOUND_BY_EXISTING_R2_MANIFEST",
         "adapter": "R2_STEP_9", "adapter_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"},
        {"arm_id": "C1_QWEN3_8B", "role": "PRIMARY_CHALLENGER", "family": "QWEN3", "architecture_scope": "TEXT_ONLY",
         "model": "Qwen/Qwen3-8B", "model_revision": "MUST_PIN_BEFORE_DOWNLOAD", "adapter": None, "thinking": "DISABLED"},
        {"arm_id": "C2_QWEN25_7B", "role": "MATURE_FAMILY_CONTROL", "family": "QWEN2_5", "architecture_scope": "TEXT_ONLY",
         "model": "Qwen/Qwen2.5-7B-Instruct", "model_revision": "MUST_PIN_BEFORE_DOWNLOAD", "adapter": None, "thinking": "NOT_APPLICABLE"},
    ],
    "excluded_initially": ["google/gemma-3-12b-it", "Qwen/Qwen3.5-9B"],
    "exclusion_reason": "MULTIMODAL_RUNTIME_CONFOUNDING_IN_TEXT_ONLY_FIRST_ROUND",
    "expansion_order": ["Qwen/Qwen3-14B", "google/gemma-3-12b-it", "Qwen/Qwen3.5-9B"],
    "runtime_binding_required": ["MODEL_REVISION", "TOKENIZER_REVISION", "CHAT_TEMPLATE_SHA256", "WEIGHT_MANIFEST", "QUANTIZATION_RECIPE", "TRANSFORMERS_VERSION", "CUDA_VERSION"],
    "quantization_policy": {
        "r2_control": "AUTHORITATIVE_EXISTING_RUNTIME_UNCHANGED",
        "challengers": "SAME_BACKEND_BIT_WIDTH_AND_QUANTIZATION_RECIPE",
        "interpretation": "DEPLOYABLE_MODEL_RUNTIME_PACKAGE_COMPARISON",
        "winner_confirmation": "REFERENCE_OR_HIGHER_PRECISION_CONFIRMATION_REQUIRED_BEFORE_PIVOT",
        "maximum_peak_vram_gib": 16,
    },
    "download_authorized": False, "model_load_authorized": False,
}, "candidates_identity")

decoding = identified({
    "schema": "editor-text-realizer-base-bakeoff-decoding", "schema_version": 1,
    "semantic_prompt_payload": "BYTE_IDENTICAL_BEFORE_NATIVE_CHAT_TEMPLATE",
    "native_chat_template": "MODEL_SPECIFIC_AND_MUST_BE_HASH_PINNED",
    "do_sample": False, "temperature": None, "top_p": None, "top_k": None,
    "repetition_penalty": 1.0, "no_repeat_ngram_size": 0, "max_new_tokens": 768,
    "qwen3_enable_thinking": False, "seed_role": "REPRODUCIBILITY_ONLY_NOT_SAMPLING",
    "proposal_schema": "SOURCE_BOUND_HYBRID_REALIZATION_SCHEMA_V1",
    "structured_decoding": "DISABLED_TO_MEASURE_NATIVE_ADHERENCE",
    "external_verifier": "BYTE_IDENTICAL_ALL_ARMS", "extractive_fallback": "BYTE_IDENTICAL_ALL_ARMS",
}, "decoding_identity")

evaluation = identified({
    "schema": "editor-text-realizer-base-bakeoff-evaluation", "schema_version": 1,
    "cases": 48, "partitions": {"DEVELOPMENT": 24, "REPLAY_RETENTION": 24},
    "source_authority": "SOURCE_BOUND_LEDGER", "oracle_scope": "FEASIBILITY_UPPER_BOUND_ONLY",
    "metrics": ["NATIVE_SCHEMA_ADHERENCE", "VERIFIER_ACCEPTANCE", "FALLBACK_RATE", "REQUIRED_ATOM_COVERAGE",
                "NOVEL_ACTOR_OR_NUMBER", "EPISTEMIC_MARKER_RETENTION", "PROCEDURAL_STATUS_RETENTION",
                "NUMBER_ROLE_FIDELITY", "SENTENCE_BUDGET", "REPETITION", "FUNCTIONAL_ROMANIAN_BLIND",
                "PEAK_VRAM_GIB", "LATENCY_SECONDS_PER_CASE", "TOKENS_PER_SECOND", "RUNTIME_FAILURE_RATE"],
    "human_blind_required_for": ["FUNCTIONAL_ROMANIAN", "NATURALNESS", "USABLE_REALIZATION_GAIN"],
    "machine_score_cannot_select_parent": True,
    "quantization_confound_control": "MATCHED_BETWEEN_QWEN_CHALLENGERS_AND_CONFIRM_WINNER_AT_REFERENCE_OR_HIGHER_PRECISION",
    "reproducibility": "ONE_PRIMARY_DETERMINISTIC_RUN_PLUS_BYTE_EXACT_REPLAY",
}, "evaluation_identity")

terminal = identified({
    "schema": "editor-text-realizer-base-bakeoff-terminal-rules", "schema_version": 1,
    "precedence": "STOP_THEN_REVISE_THEN_CONTINUE",
    "STOP": ["ANY_ACCEPTED_NOVEL_ACTOR_OR_NUMBER", "ANY_ACCEPTED_EPISTEMIC_OR_PROCEDURAL_UPGRADE",
             "HISTORICAL_HOLDOUT_ACCESS", "MODEL_OR_TOKENIZER_IDENTITY_UNBOUND", "VRAM_EXCEEDS_16_GIB_OR_RUNTIME_UNSTABLE"],
    "REVISE": ["FALLBACK_RATE_ABOVE_25_PERCENT", "NO_BLIND_REALIZATION_GAIN_OVER_EXTRACTIVE",
               "CHALLENGER_GAIN_NOT_BYTE_REPRODUCIBLE"],
    "CONTINUE": ["ZERO_ACCEPTED_FACTUAL_OR_EPISTEMIC_DRIFT", "FALLBACK_RATE_AT_MOST_25_PERCENT",
                 "BLIND_FUNCTIONAL_ROMANIAN_GAIN_OVER_R2", "BYTE_REPRODUCIBLE", "RTX5080_16GB_RUNTIME_PASS"],
    "PIVOT_GATE": ["ALL_CONTINUE_CONDITIONS", "CONFIRMATORY_EVALUATION_REQUIRED", "NO_PARENT_SELECTION_FROM_THIS_DIAGNOSTIC"],
    "EXPANSION_GATE": "OPEN_QWEN3_14B_THEN_MULTIMODAL_ONLY_IF_NO_INITIAL_CHALLENGER_PASSES_AND_FAILURE_IS_CAPACITY_COMPATIBLE",
    "parent_selection_authority": False,
}, "decision_identity")

protocol = identified({
    "schema": "editor-text-realizer-base-bakeoff-protocol", "schema_version": 1,
    "objective": "SELECT_A_TEXT_ONLY_REALIZER_CANDIDATE_FOR_SOURCE_BOUND_EDITOR_ARCHITECTURE",
    "published_hybrid_checkpoint": "1262155e331b2a44a259fe824ad2d634649a7a96",
    "hybrid_result_identity": "9249ed123adebeeff71af67852c1d21ace60993ae5dcbcadb3f81e5707af2921",
    "contract_identity": "67a5cd5813d422c513795dd88b561db3f74a55ee2a932d8bcb2d0d1035eb0b37",
    "hybrid_pack_identity": "bbad139fde613c1c912cd53992b4c2be047d73180f6a6ae732dc6348461d28f9",
    "hybrid_protocol_identity": "5a5ef79af85a3b58b3c0e2f46be3f9e3dd573d75dae361c6d6df88588f7c1aea",
    "candidates_identity": candidates["candidates_identity"], "decoding_identity": decoding["decoding_identity"],
    "evaluation_identity": evaluation["evaluation_identity"], "decision_identity": terminal["decision_identity"],
    "baseline": "R2_STEP_9", "successor_training": "SUSPENDED", "historical_holdouts_allowed": False,
    "download_authorized": False, "model_load_authorized": False, "inference_authorized": False,
    "optimizer_creation_authorized": False, "training_authorized": False, "parent_selection_authority": False,
    "promotion_authorized": False, "release_authorized": False, "cleanup_authorized": False,
    "base_weight_only_causal_claim_allowed": False,
}, "protocol_identity")

files = {
    f"{PREFIX}-candidates.json": candidates,
    f"{PREFIX}-decoding.json": decoding,
    f"{PREFIX}-evaluation.json": evaluation,
    f"{PREFIX}-terminal-rules.json": terminal,
    f"{PREFIX}-protocol.json": protocol,
}
for name, value in files.items():
    write(name, value)

manifest_core = {
    "schema": "editor-text-realizer-base-bakeoff-pack", "schema_version": 1,
    "protocol_identity": protocol["protocol_identity"], "files": {name: sha((ART / name).read_bytes()) for name in sorted(files)},
    "source_files": {
        "editor-core-factual-setup-contract-v1.json": sha((ART / "editor-core-factual-setup-contract-v1.json").read_bytes()),
        "editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl": sha((ART / "editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl").read_bytes()),
        "editor-core-source-bound-hybrid-feasibility-v1-realization-schema.json": sha((ART / "editor-core-source-bound-hybrid-feasibility-v1-realization-schema.json").read_bytes()),
        "editor-core-source-bound-hybrid-closed-semantic-result-v1.json": sha((ART / "editor-core-source-bound-hybrid-closed-semantic-result-v1.json").read_bytes()),
    },
    "fixture_only": True, "models_downloaded": False, "model_loaded": False, "inference_performed": False,
    "optimizer_created": False, "training_performed": False, "historical_holdouts_read": False,
}
manifest = identified(manifest_core, "pack_identity")
write(f"{PREFIX}-manifest.json", manifest)
print(json.dumps({"status": "PASS_BUILD", "pack_identity": manifest["pack_identity"], "protocol_identity": protocol["protocol_identity"]}, sort_keys=True))
