"""Tokenizer-only trie compatibility profile for Stage P Scope Graph V1."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
import types
from pathlib import Path


MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ROOT = Path("/mnt/c/Projects/pastila-news-monitor")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _creative(entry_id="P1", relation="CREATIVE_HOST"):
    return {"entry_id": entry_id, "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metaforă",
            "authority_support": None, "commitment": "Vehicul editorial specific poveștii.",
            "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
            "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
            "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
            "independence_group": "G1", "scope_relation": relation,
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _real(entry_id="P2", relation="FACTUAL_RETURN_WITHIN_CREATIVE_HOST"):
    return {"entry_id": entry_id, "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": "fapt guvernat",
            "authority_support": "fapt guvernat", "commitment": "Faptul guvernat rămâne afirmat.",
            "scope_basis": "ASSERTED", "event_alignment": "GOVERNED_EVENT",
            "authority_modality": "CERTAIN_OR_ACTUAL", "candidate_modality": "CERTAIN_OR_ACTUAL",
            "authority_timing": "PAST", "candidate_timing": "PAST", "independence_group": "G2",
            "scope_relation": relation, "creative_host_entry_id": "P1" if relation != "STANDALONE" else None,
            "factual_return_basis": "ASSERTION_SURVIVES"}


def _unresolved():
    return {"entry_id": "P1", "entry_type": "UNRESOLVED_SCOPE", "candidate_span": "subspan ambiguu",
            "authority_support": None, "commitment": "Relație semantică nerezolvată.", "scope_basis": "UNRESOLVED",
            "event_alignment": "UNRESOLVED", "authority_modality": "NOT_APPLICABLE",
            "candidate_modality": "UNRESOLVED", "authority_timing": "NOT_APPLICABLE",
            "candidate_timing": "UNRESOLVED", "independence_group": "G1",
            "scope_relation": "UNRESOLVED_RELATION", "creative_host_entry_id": None,
            "factual_return_basis": "UNRESOLVED"}


def _raw(entries, complete=True):
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": entries,
             "coverage_receipt": {"candidate_reviewed_as_whole": complete,
                                  "embedded_propositions_checked": complete,
                                  "creative_scope_checked": complete,
                                  "unresolved_scope_present": not complete,
                                  "overlapping_spans_reconciled": complete,
                                  "integrated_creative_hosts_checked": complete,
                                  "factual_return_tests_completed": complete},
             "coverage_decision": "COMPLETE" if complete else "INDETERMINATE"}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main():
    started = time.perf_counter()
    from transformers import AutoTokenizer

    package_root = ROOT / "src/pastila_scout"
    semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    _load(prefix + "stage_p_role_coherence_constraint_v1", semantic_root / "stage_p_role_coherence_constraint_v1.py")
    _load(prefix + "stage_p_role_coherence_constraint_v2", semantic_root / "stage_p_role_coherence_constraint_v2.py")
    dfa = _load(prefix + "stage_p_scope_graph_constraint_v1", semantic_root / "stage_p_scope_graph_constraint_v1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    projector = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    pieces = {token: tokenizer.decode([token], skip_special_tokens=True) for token in range(len(tokenizer))}
    trie = projector.StagePTokenTrieProjectorV1(
        token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id})
    State = dfa.StagePScopeGraphConstraintStateV1
    fixtures = (("PURE_CREATIVE_HOST", _raw([_creative()])),
                ("EMBEDDED_FACTUAL_RETURN", _raw([_creative(), _real()])),
                ("STANDALONE_FACTUAL", _raw([_real(entry_id="P1", relation="STANDALONE")])),
                ("INDETERMINATE_SCOPE", _raw([_unresolved()], complete=False)))
    streams = []
    for label, raw in fixtures:
        ids = tokenizer.encode(raw, add_special_tokens=False)
        invalid = []
        for index, token in enumerate(ids):
            state = State().feed(tokenizer.decode(ids[:index], skip_special_tokens=True))
            if token not in trie.allowed_token_ids(state):
                invalid.append(index)
                break
        decoded = tokenizer.decode(ids, skip_special_tokens=True)
        final = State().feed(decoded)
        streams.append({"label": label, "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "tokens": len(ids), "decoded_exact": decoded == raw,
                        "invalid_next_token_indices": invalid, "terminal_state": final.can_eos,
                        "eos_only_after_terminal": trie.allowed_token_ids(final) == (tokenizer.eos_token_id,)})
    passed = all(item["decoded_exact"] and not item["invalid_next_token_indices"] and
                 item["terminal_state"] and item["eos_only_after_terminal"] for item in streams)
    print(json.dumps({"schema_name": "pastila-semantic-admission-v2-stage-p-scope-graph-real-tokenizer-preflight",
                      "schema_version": "1.0.0", "result": "PASS" if passed else "FAIL",
                      "tokenizer_path": str(MODEL), "tokenizer_vocabulary_size": len(tokenizer),
                      "tokenizer_identity": "sha256:" + hashlib.sha256((str(MODEL) + "\n" + str(len(tokenizer))).encode()).hexdigest(),
                      "trie_nodes": trie.trie_node_count, "trie_cache_size": trie.cache_size,
                      "streams": streams, "elapsed_seconds": round(time.perf_counter() - started, 6),
                      "torch_imported_transitively": "torch" in sys.modules, "model_imported": False,
                      "model_load_started": False, "inference_started": False, "model_calls": 0,
                      "provider_calls": 0, "runner_calls": 0}, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
