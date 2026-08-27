"""Real-tokenizer, zero-inference compatibility check for Construction Role Audit V1."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import types
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ledger() -> str:
    entry = {"entry_id": "P1", "entry_type": "REAL_WORLD_COMMITMENT",
        "candidate_span": "Raport literal.", "authority_support": "Raport literal.",
        "commitment": "Raport literal.", "scope_basis": "ASSERTED",
        "event_alignment": "GOVERNED_EVENT", "authority_modality": "CERTAIN_OR_ACTUAL",
        "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "PRESENT",
        "candidate_timing": "PRESENT", "independence_group": "G1", "scope_relation": "STANDALONE",
        "creative_host_entry_id": None, "factual_return_basis": "ASSERTION_SURVIVES"}
    value = {"stage_id": "PROPOSITION_LEDGER", "construction_role_audit": {
        "candidate_reviewed_as_construction": True,
        "overall_disposition": "NO_MATERIAL_CREATIVE_CONSTRUCTION",
        "construction_records": [{"construction_id": "C1", "candidate_span": "Raport literal.",
            "construction_role": "LITERAL_ONLY", "role_basis": "Sens literal.",
            "creative_host_entry_id": None, "literal_or_return_entry_ids": ["P1"],
            "resolution": "LITERAL_PATH_RETAINED"}], "literal_path_basis": "Sens literal."},
        "entries": [entry], "creative_target_audits": [], "coverage_receipt": {
            "candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
            "creative_scope_checked": True, "unresolved_scope_present": False,
            "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
            "factual_return_tests_completed": True, "creative_targets_enumerated": True,
            "target_classes_reviewed": True, "target_to_ledger_reconciled": True,
            "construction_roles_reviewed": True, "construction_to_ledger_reconciled": True},
        "coverage_decision": "COMPLETE"}
    return json.dumps(value, separators=(",", ":"))


def main() -> None:
    package_root = ROOT / "src/pastila_scout"
    semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    modules = ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
               "stage_p_scope_graph_constraint_v1", "stage_p_scope_graph_constraint_v1_1",
               "stage_p_scope_graph_constraint_v1_2", "stage_p_creative_target_constraint_v1")
    for module in modules:
        _load(prefix + module, semantic_root / f"{module}.py")
    construction = _load(prefix + "stage_p_construction_role_constraint_v1",
                         semantic_root / "stage_p_construction_role_constraint_v1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    trie = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    pieces = {token_id: tokenizer.decode([token_id], skip_special_tokens=True)
              for token_id in range(len(tokenizer))}
    projector = trie.StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id})
    raw = _ledger()
    markers = ('"construction_role_audit":', '"overall_disposition":"', '"construction_role":"',
               '"entries":[', '"creative_target_audits":[', '"coverage_decision":"')
    prefixes = [""] + [raw.split(marker, 1)[0] + marker for marker in markers] + [raw]
    rows = []
    started = time.perf_counter()
    for current in prefixes:
        state = construction.StagePConstructionRoleConstraintStateV1().feed(current)
        before = time.perf_counter(); allowed = projector.allowed_token_ids(state); elapsed = time.perf_counter() - before
        rows.append({"prefix_bytes": len(current.encode()), "allowed_count": len(allowed),
                     "can_eos": state.can_eos, "seconds": round(elapsed, 6)})
    result = {"result": "PASS", "state_count": len(rows), "states": rows,
        "matrix_seconds": round(time.perf_counter() - started, 6), "vocabulary_size": len(tokenizer),
        "trie_node_count": projector.trie_node_count, "model_loads": 0, "model_calls": 0,
        "provider_calls": 0, "inference_calls": 0, "case01_executed": False, "stage_c_calls": 0,
        "peft_loaded": any(name.startswith("peft") for name in sys.modules)}
    passed = (all(row["allowed_count"] > 0 for row in rows) and rows[-1]["can_eos"]
              and rows[-1]["allowed_count"] == 1 and result["matrix_seconds"] <= 30
              and not result["peft_loaded"])
    result["result"] = "PASS" if passed else "FAIL"
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
