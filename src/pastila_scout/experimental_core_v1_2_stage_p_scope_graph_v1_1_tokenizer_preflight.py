"""Tokenizer-only trie compatibility profile for Stage P Scope Graph V1.1."""
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
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


def _creative(entry_id="P1"):
    return {"entry_id": entry_id, "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metaforă",
            "authority_support": None, "commitment": "Vehicul editorial specific poveștii.",
            "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
            "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
            "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
            "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _real(*, entry_id="P1", support=None, event="NEW_UNSUPPORTED_EVENT", relation="STANDALONE", host=None):
    supported = support is not None
    return {"entry_id": entry_id, "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": "fapt guvernat",
            "authority_support": support, "commitment": "Propoziție reală purtată de candidat.",
            "scope_basis": "ASSERTED", "event_alignment": event,
            "authority_modality": "CERTAIN_OR_ACTUAL" if supported else "NOT_APPLICABLE",
            "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "PAST" if supported else "NOT_APPLICABLE",
            "candidate_timing": "PAST", "independence_group": "G2", "scope_relation": relation,
            "creative_host_entry_id": host, "factual_return_basis": "ASSERTION_SURVIVES"}


def _raw(entries):
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": entries,
             "coverage_receipt": {"candidate_reviewed_as_whole": True,
                                  "embedded_propositions_checked": True, "creative_scope_checked": True,
                                  "unresolved_scope_present": False, "overlapping_spans_reconciled": True,
                                  "integrated_creative_hosts_checked": True, "factual_return_tests_completed": True},
             "coverage_decision": "COMPLETE"}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main():
    started = time.perf_counter()
    from transformers import AutoTokenizer
    package_root = ROOT / "src/pastila_scout"; semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    for module in ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
                   "stage_p_scope_graph_constraint_v1"):
        _load(prefix + module, semantic_root / f"{module}.py")
    dfa = _load(prefix + "stage_p_scope_graph_constraint_v1_1", semantic_root / "stage_p_scope_graph_constraint_v1_1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    projector = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    pieces = {token: tokenizer.decode([token], skip_special_tokens=True) for token in range(len(tokenizer))}
    trie = projector.StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id})
    State = dfa.StagePScopeGraphConstraintStateV1_1
    fixtures = (("PURE_CREATIVE", _raw([_creative()])),
                ("NULL_UNSUPPORTED", _raw([_real()])),
                ("SUPPORTED_GOVERNED", _raw([_real(support="fapt guvernat", event="GOVERNED_EVENT")])),
                ("PARTIAL_SUPPORT_UNSUPPORTED", _raw([_real(support="fapt")])),
                ("HOST_WITH_GOVERNED_LITERAL", _raw([_creative(), _real(entry_id="P2", support="fapt guvernat",
                    event="GOVERNED_EVENT", relation="FACTUAL_RETURN_WITHIN_CREATIVE_HOST", host="P1")])) )
    streams = []
    for label, raw in fixtures:
        ids = tokenizer.encode(raw, add_special_tokens=False); invalid = []
        for index, token in enumerate(ids):
            state = State().feed(tokenizer.decode(ids[:index], skip_special_tokens=True))
            if token not in trie.allowed_token_ids(state): invalid.append(index); break
        decoded = tokenizer.decode(ids, skip_special_tokens=True); final = State().feed(decoded)
        streams.append({"label": label, "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(), "tokens": len(ids),
                        "decoded_exact": decoded == raw, "invalid_next_token_indices": invalid,
                        "terminal_state": final.can_eos,
                        "eos_only_after_terminal": trie.allowed_token_ids(final) == (tokenizer.eos_token_id,)})
    invalid_raw = _raw([_real(event="GOVERNED_EVENT")]); invalid_ids = tokenizer.encode(invalid_raw, add_special_tokens=False)
    blocked = None
    for index, token in enumerate(invalid_ids):
        state = State().feed(tokenizer.decode(invalid_ids[:index], skip_special_tokens=True))
        if token not in trie.allowed_token_ids(state): blocked = index; break
    passed = all(item["decoded_exact"] and not item["invalid_next_token_indices"] and item["terminal_state"] and
                 item["eos_only_after_terminal"] for item in streams) and blocked is not None
    print(json.dumps({"schema_name": "pastila-semantic-admission-v2-stage-p-scope-graph-v1-1-tokenizer-preflight",
        "schema_version": "1.0.0", "result": "PASS" if passed else "FAIL", "tokenizer_path": str(MODEL),
        "tokenizer_vocabulary_size": len(tokenizer),
        "tokenizer_identity": "sha256:" + hashlib.sha256((str(MODEL) + "\n" + str(len(tokenizer))).encode()).hexdigest(),
        "trie_nodes": trie.trie_node_count, "trie_cache_size": trie.cache_size, "streams": streams,
        "invalid_null_support_governed_first_blocked_token_index": blocked,
        "elapsed_seconds": round(time.perf_counter() - started, 6), "torch_imported_transitively": "torch" in sys.modules,
        "model_imported": False, "model_load_started": False, "inference_started": False,
        "model_calls": 0, "provider_calls": 0, "runner_calls": 0}, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
