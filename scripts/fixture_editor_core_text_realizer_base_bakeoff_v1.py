"""Fixture-only executable boundary for the controlled text-realizer bake-off."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fixture_editor_core_source_bound_hybrid_feasibility_v1 import (
    execute_with_fallback, extractive_proposal, validate_ledger, verify_proposal,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-text-realizer-base-bakeoff-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def identity(value: dict, key: str) -> None:
    core = {name: item for name, item in value.items() if name != key}
    if value[key] != sha(canonical(core)):
        raise ValueError(f"identity mismatch: {key}")


def run() -> dict:
    manifest = load(f"{PREFIX}-manifest.json")
    protocol = load(f"{PREFIX}-protocol.json")
    candidates = load(f"{PREFIX}-candidates.json")
    decoding = load(f"{PREFIX}-decoding.json")
    evaluation = load(f"{PREFIX}-evaluation.json")
    terminal = load(f"{PREFIX}-terminal-rules.json")
    for value, key in ((manifest, "pack_identity"), (protocol, "protocol_identity"), (candidates, "candidates_identity"),
                       (decoding, "decoding_identity"), (evaluation, "evaluation_identity"), (terminal, "decision_identity")):
        identity(value, key)
    for name, expected in manifest["files"].items():
        if sha((ART / name).read_bytes()) != expected:
            raise ValueError(f"manifest mismatch: {name}")
    for name, expected in manifest["source_files"].items():
        if sha((ART / name).read_bytes()) != expected:
            raise ValueError(f"source manifest mismatch: {name}")
    contract = load("editor-core-factual-setup-contract-v1.json")
    hybrid_manifest = load("editor-core-source-bound-hybrid-feasibility-v1-manifest.json")
    hybrid_result = load("editor-core-source-bound-hybrid-closed-semantic-result-v1.json")
    if protocol["contract_identity"] != contract["contract_identity"]:
        raise ValueError("contract binding drift")
    if protocol["hybrid_pack_identity"] != hybrid_manifest["pack_identity"]:
        raise ValueError("hybrid pack binding drift")
    if protocol["hybrid_result_identity"] != hybrid_result["result_identity"]:
        raise ValueError("hybrid result binding drift")
    if [arm["arm_id"] for arm in candidates["initial_arms"]] != ["C0_R2_MINISTRAL", "C1_QWEN3_8B", "C2_QWEN25_7B"]:
        raise ValueError("candidate scope drift")
    if any(arm["architecture_scope"] != "TEXT_ONLY" for arm in candidates["initial_arms"][1:]):
        raise ValueError("multimodal challenger entered initial round")
    if candidates["quantization_policy"]["challengers"] != "SAME_BACKEND_BIT_WIDTH_AND_QUANTIZATION_RECIPE":
        raise ValueError("challenger quantization confound")
    if candidates["quantization_policy"]["winner_confirmation"] != "REFERENCE_OR_HIGHER_PRECISION_CONFIRMATION_REQUIRED_BEFORE_PIVOT":
        raise ValueError("winner confirmation missing")
    if decoding["do_sample"] or decoding["qwen3_enable_thinking"] or decoding["structured_decoding"] != "DISABLED_TO_MEASURE_NATIVE_ADHERENCE":
        raise ValueError("decoding confound")
    forbidden = ("download_authorized", "model_load_authorized", "inference_authorized", "optimizer_creation_authorized",
                 "training_authorized", "parent_selection_authority", "promotion_authorized", "release_authorized", "cleanup_authorized")
    if any(protocol[key] for key in forbidden):
        raise ValueError("forbidden authority enabled")
    ledgers = [json.loads(line) for line in (ART / "editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(ledgers) != 48:
        raise ValueError("ledger inventory")
    accepted = fallback = 0
    for ledger in ledgers:
        validate_ledger(ledger)
        proposal = extractive_proposal(ledger)
        for _arm in candidates["initial_arms"]:
            if not verify_proposal(ledger, proposal)["accepted"]:
                raise ValueError("valid proposal rejected")
            accepted += 1
            invalid = json.loads(json.dumps(proposal))
            invalid["sentences"][0]["text"] += " 999999."
            result = execute_with_fallback(ledger, invalid)
            if result["route"] != "EXTRACTIVE_FALLBACK":
                raise ValueError("invalid proposal escaped fallback")
            fallback += 1
    return {
        "status": "PASS_FIXTURE_ONLY", "pack_identity": manifest["pack_identity"],
        "protocol_identity": protocol["protocol_identity"], "arms": 3, "cases": 48, "source_bindings": 4,
        "valid_acceptances": accepted, "adversarial_fallbacks": fallback,
        "models_downloaded": False, "model_loaded": False, "inference_performed": False,
        "optimizer_created": False, "training_performed": False, "historical_holdouts_read": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
