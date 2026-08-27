"""Real-tokenizer, zero-inference trie compatibility check for target decomposition."""
from __future__ import annotations

import json
import importlib.util
import sys
import time
import types
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


def _entry():
    return {"entry_id": "P1", "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metafora",
        "authority_support": None, "commitment": "Transformare editoriala.",
        "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
        "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
        "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
        "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
        "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _ledger():
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": [_entry()],
        "creative_target_audits": [{"audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span": "metafora", "semantic_target": "Evaluare editoriala.",
            "target_class": "NONFACTUAL_EDITORIAL_OR_CREATIVE",
            "survival_basis": "DOES_NOT_SURVIVE_AS_FACT", "proposition_entry_id": None,
            "resolution": "RETAINED_NONFACTUAL"}], "coverage_receipt": {
            "candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
            "creative_scope_checked": True, "unresolved_scope_present": False,
            "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
            "factual_return_tests_completed": True, "creative_targets_enumerated": True,
            "target_classes_reviewed": True, "target_to_ledger_reconciled": True},
        "coverage_decision": "COMPLETE"}, separators=(",", ":"))


def main():
    package_root = ROOT / "src/pastila_scout"; semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    for module in ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
                   "stage_p_scope_graph_constraint_v1", "stage_p_scope_graph_constraint_v1_1",
                   "stage_p_scope_graph_constraint_v1_2"):
        loaded = _load(prefix + module, semantic_root / f"{module}.py")
    target_module = _load(prefix + "stage_p_creative_target_constraint_v1",
                          semantic_root / "stage_p_creative_target_constraint_v1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    trie_module = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    StagePCreativeTargetConstraintStateV1 = target_module.StagePCreativeTargetConstraintStateV1
    StagePTokenTrieProjectorV1 = trie_module.StagePTokenTrieProjectorV1
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in range(len(tokenizer))}
    projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id})
    raw = _ledger()
    prefixes = ["", raw.split('"entry_type":"', 1)[0] + '"entry_type":"',
        raw.split('"creative_target_audits":[', 1)[0] + '"creative_target_audits":[',
        raw.split('"target_class":"', 1)[0] + '"target_class":"',
        raw.split('"survival_basis":"', 1)[0] + '"survival_basis":"',
        raw.split('"coverage_decision":"', 1)[0] + '"coverage_decision":"', raw]
    rows = []; started = time.perf_counter()
    for prefix in prefixes:
        state = StagePCreativeTargetConstraintStateV1().feed(prefix)
        before = time.perf_counter(); allowed = projector.allowed_token_ids(state); elapsed = time.perf_counter() - before
        rows.append({"prefix_bytes": len(prefix.encode()), "allowed_count": len(allowed),
                     "can_eos": state.can_eos, "seconds": round(elapsed, 6)})
    result = {"result": "PASS", "state_count": len(rows), "states": rows,
        "matrix_seconds": round(time.perf_counter() - started, 6), "vocabulary_size": len(tokenizer),
        "trie_node_count": projector.trie_node_count,
        "transformers_loaded_for_tokenizer_only": "transformers" in sys.modules,
        "peft_loaded": any(name.startswith("peft") for name in sys.modules),
        "model_loads": 0, "model_calls": 0, "provider_calls": 0, "inference_calls": 0,
        "case01_executed": False, "stage_c_calls": 0}
    passed = (all(row["allowed_count"] > 0 for row in rows) and rows[-1]["can_eos"]
              and rows[-1]["allowed_count"] == 1 and result["matrix_seconds"] <= 30
              and not result["peft_loaded"])
    result["result"] = "PASS" if passed else "FAIL"
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if not passed: raise SystemExit(1)


if __name__ == "__main__": main()
