"""Real-tokenizer timing/equivalence matrix for the baseline-language adapter."""
from __future__ import annotations

import importlib.util
import json
import statistics
import sys
import time
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
HEARTBEAT = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-b-case01-probe-run-v1-evidence/durable-lifecycle/6860c28d5925b279c61193179e4c26dd8d0764e4b62fa59e23cf7e2261df21c0/runner-00014-generation-heartbeat.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


def _ledger(*, unresolved: bool) -> str:
    if unresolved:
        entry = {"entry_id": "P1", "entry_type": "UNRESOLVED_SCOPE", "candidate_span": "x",
                 "authority_support": None, "commitment": "Nerezolvat.", "scope_basis": "UNRESOLVED",
                 "event_alignment": "UNRESOLVED", "authority_modality": "NOT_APPLICABLE",
                 "candidate_modality": "UNRESOLVED", "authority_timing": "NOT_APPLICABLE",
                 "candidate_timing": "UNRESOLVED", "independence_group": "G1",
                 "scope_relation": "UNRESOLVED_RELATION", "creative_host_entry_id": None,
                 "factual_return_basis": "UNRESOLVED"}
    else:
        entry = {"entry_id": "P1", "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metafora",
                 "authority_support": None, "commitment": "Transformare editoriala.",
                 "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
                 "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
                 "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
                 "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
                 "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": [entry], "coverage_receipt": {
        "candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
        "creative_scope_checked": True, "unresolved_scope_present": unresolved,
        "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
        "factual_return_tests_completed": True},
        "coverage_decision": "INDETERMINATE" if unresolved else "COMPLETE"}, separators=(",", ":"))


def main() -> None:
    package_root = ROOT / "src/pastila_scout"; semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    for module in ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
                   "stage_p_scope_graph_constraint_v1", "stage_p_scope_graph_constraint_v1_1"):
        _load(prefix + module, semantic_root / f"{module}.py")
    dfa = _load(prefix + "stage_p_scope_graph_constraint_v1_2", semantic_root / "stage_p_scope_graph_constraint_v1_2.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    baseline_module = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    _load(prefix + "stage_p_liveness_trie_projector_v1", semantic_root / "stage_p_liveness_trie_projector_v1.py")
    candidate_module = _load(prefix + "stage_p_diagnostic_trie_projector_v1",
                             semantic_root / "stage_p_diagnostic_trie_projector_v1.py")

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in range(len(tokenizer))}
    kwargs = {"token_pieces": pieces, "eos_token_id": tokenizer.eos_token_id,
              "excluded_token_ids": set(tokenizer.all_special_ids) - {tokenizer.eos_token_id}}
    baseline = baseline_module.StagePTokenTrieProjectorV1(**kwargs)
    candidate = candidate_module.StagePDiagnosticTokenTrieProjectorV1(**kwargs)
    State = dfa.StagePScopeGraphConstraintStateV1_2
    complete = _ledger(unresolved=False); unresolved = _ledger(unresolved=True)
    entry_choice = complete.split('CONTAINED_CREATIVE', 1)[0]
    candidate_start = complete.split('"candidate_span":', 1)[0] + '"candidate_span":'
    candidate_empty = candidate_start + '"'
    authority = candidate_start + '"x","authority_support":'
    coverage_complete = complete.split('"coverage_decision":"', 1)[0] + '"coverage_decision":"'
    coverage_unresolved = unresolved.split('"coverage_decision":"', 1)[0] + '"coverage_decision":"'
    heartbeat = json.loads(HEARTBEAT.read_text("utf-8"))["partial_output"]
    states = {
        "initial_literal": State(), "entry_type_choice": State().feed(entry_choice),
        "candidate_string_start": State().feed(candidate_start), "candidate_string_empty": State().feed(candidate_empty),
        "candidate_string_1": State().feed(candidate_empty + "x"),
        "candidate_string_64": State().feed(candidate_empty + "x" * 64),
        "candidate_string_256": State().feed(candidate_empty + "x" * 256),
        "authority_nullable": State().feed(authority), "coverage_complete": State().feed(coverage_complete),
        "coverage_indeterminate": State().feed(coverage_unresolved), "timeout_heartbeat": State().feed(heartbeat),
    }
    rows = []; exact = True; candidate_total = baseline_total = 0.0; warm = []
    for name, state in states.items():
        baseline._cache.clear(); start = time.perf_counter(); left = baseline.allowed_token_ids(state); bt = time.perf_counter() - start
        candidate._cache.clear(); start = time.perf_counter(); right = candidate.allowed_token_ids(state); ct = time.perf_counter() - start
        exact = exact and left == right; baseline_total += bt; candidate_total += ct
        candidate.allowed_token_ids(state)
        samples = []
        for _ in range(20):
            start = time.perf_counter(); candidate.allowed_token_ids(state); samples.append(time.perf_counter() - start)
        warm.extend(samples)
        rows.append({"state": name, "allowed_count": len(right), "sets_equal": left == right,
                     "baseline_cold_seconds": round(bt, 6), "candidate_cold_seconds": round(ct, 6),
                     "candidate_warm_p95_seconds": round(sorted(samples)[18], 6)})
    baseline_median = statistics.median(row["baseline_cold_seconds"] for row in rows)
    candidate_median = statistics.median(row["candidate_cold_seconds"] for row in rows)
    ratio = candidate_median / baseline_median if baseline_median else 1.0
    result = {"schema_name": "pastila-stage-p-diagnostic-projector-real-tokenizer-evidence",
        "schema_version": "1.0.0-evaluation.1", "result": "PASS", "states": rows,
        "allowed_set_equivalence": exact, "state_count": len(rows),
        "maximum_candidate_cold_seconds": max(row["candidate_cold_seconds"] for row in rows),
        "candidate_matrix_seconds": round(candidate_total, 6), "baseline_matrix_seconds": round(baseline_total, 6),
        "candidate_to_baseline_median_ratio": round(ratio, 6), "warm_p95_seconds": round(sorted(warm)[int(len(warm)*.95)-1], 6),
        "tokenizer_vocabulary_size": len(tokenizer), "trie_node_count": candidate.trie_node_count,
        "peft_imported": any(name.startswith("peft") for name in sys.modules),
        "model_loads": 0, "model_calls": 0, "provider_calls": 0, "inference_calls": 0,
        "case01_executed": False}
    passed = (exact and result["maximum_candidate_cold_seconds"] <= 5 and result["candidate_matrix_seconds"] <= 30
              and result["warm_p95_seconds"] <= .25 and ratio <= 1.25 and not result["peft_imported"])
    result["result"] = "PASS" if passed else "FAIL"
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
