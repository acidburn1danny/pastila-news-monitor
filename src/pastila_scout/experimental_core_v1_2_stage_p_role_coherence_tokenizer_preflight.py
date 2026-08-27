"""WSL tokenizer-only trie compatibility profile for Stage P Role Coherence V1."""
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


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _entry(entry_type: str) -> dict[str, object]:
    if entry_type == "CONTAINED_CREATIVE":
        return {
            "entry_id": "P1", "entry_type": entry_type, "candidate_span": "hotelul",
            "authority_support": None, "commitment": "Camera și transparența extind editorial plata ascunsă fără un eveniment nou.",
            "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
            "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
            "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE", "independence_group": "G1",
        }
    return {
        "entry_id": "P1", "entry_type": "UNRESOLVED_SCOPE", "candidate_span": "hotelul",
        "authority_support": None, "commitment": "Rol semantic nerezolvat pentru subspanul selectat.",
        "scope_basis": "UNRESOLVED", "event_alignment": "UNRESOLVED",
        "authority_modality": "NOT_APPLICABLE", "candidate_modality": "UNRESOLVED",
        "authority_timing": "NOT_APPLICABLE", "candidate_timing": "UNRESOLVED", "independence_group": "G1",
    }


def _ledger(entry_type: str) -> str:
    complete = entry_type == "CONTAINED_CREATIVE"
    value = {
        "stage_id": "PROPOSITION_LEDGER", "entries": [_entry(entry_type)],
        "coverage_receipt": {"candidate_reviewed_as_whole": complete, "embedded_propositions_checked": complete,
                             "creative_scope_checked": complete, "unresolved_scope_present": not complete},
        "coverage_decision": "COMPLETE" if complete else "INDETERMINATE",
    }
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    started = time.perf_counter()
    from transformers import AutoTokenizer

    package_root = ROOT / "src/pastila_scout"
    semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    dfa = _load(prefix + "stage_p_role_coherence_constraint_v1", semantic_root / "stage_p_role_coherence_constraint_v1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    projector_module = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    State = dfa.StagePRoleCoherenceConstraintStateV1
    Trie = projector_module.StagePTokenTrieProjectorV1

    tokenizer_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    tokenizer_seconds = time.perf_counter() - tokenizer_started
    pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in range(len(tokenizer))}
    excluded = set(tokenizer.all_special_ids) - {tokenizer.eos_token_id}
    trie_started = time.perf_counter()
    trie = Trie(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id, excluded_token_ids=excluded)
    trie_seconds = time.perf_counter() - trie_started

    streams = []
    for label, raw in (("COMPLETE_CONTAINED_CREATIVE", _ledger("CONTAINED_CREATIVE")),
                       ("INDETERMINATE_UNRESOLVED", _ledger("UNRESOLVED_SCOPE"))):
        ids = tokenizer.encode(raw, add_special_tokens=False)
        invalid_next = []
        for index in range(len(ids)):
            decoded = tokenizer.decode(ids[:index], skip_special_tokens=True)
            state = State().feed(decoded)
            if ids[index] not in trie.allowed_token_ids(state):
                invalid_next.append(index)
                break
        decoded = tokenizer.decode(ids, skip_special_tokens=True)
        final = State().feed(decoded)
        streams.append({
            "label": label, "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(), "tokens": len(ids),
            "decoded_exact": decoded == raw, "invalid_next_token_indices": invalid_next,
            "terminal_state": final.can_eos, "eos_only_after_terminal": trie.allowed_token_ids(final) == (tokenizer.eos_token_id,),
        })
    passed = all(item["decoded_exact"] and not item["invalid_next_token_indices"] and item["terminal_state"]
                 and item["eos_only_after_terminal"] for item in streams)
    value = {
        "schema_name": "pastila-semantic-admission-v2-stage-p-role-coherence-real-tokenizer-preflight",
        "schema_version": "1.0.0", "result": "PASS" if passed else "FAIL",
        "tokenizer_path": str(MODEL), "tokenizer_vocabulary_size": len(tokenizer),
        "tokenizer_seconds": round(tokenizer_seconds, 6), "trie_nodes": trie.trie_node_count,
        "trie_build_seconds": round(trie_seconds, 6), "trie_cache_size": trie.cache_size,
        "streams": streams, "elapsed_seconds": round(time.perf_counter() - started, 6),
        "torch_imported": "torch" in sys.modules, "model_imported": False, "model_load_started": False,
        "adapter_load_started": False, "inference_started": False, "model_calls": 0, "provider_calls": 0,
    }
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
