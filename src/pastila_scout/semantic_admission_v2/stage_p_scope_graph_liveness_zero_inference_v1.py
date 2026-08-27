"""Real-tokenizer, zero-model characterization for the Track-A liveness candidate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
EVENT = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence/durable-lifecycle/d76ffd3e97cd48fa3860beedf82175146021a03edd3406d182e018a7a9ca76c1/runner-00032-generation-heartbeat.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    from transformers import AutoTokenizer
    package_root = ROOT / "src/pastila_scout"
    semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    for module in ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
                   "stage_p_scope_graph_constraint_v1"):
        _load(prefix + module, semantic_root / f"{module}.py")
    dfa = _load(prefix + "stage_p_scope_graph_constraint_v1_1",
                semantic_root / "stage_p_scope_graph_constraint_v1_1.py")
    dfa_candidate = _load(prefix + "stage_p_scope_graph_constraint_v1_2",
                          semantic_root / "stage_p_scope_graph_constraint_v1_2.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    baseline_module = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    candidate_module = _load(prefix + "stage_p_liveness_trie_projector_v1",
                             semantic_root / "stage_p_liveness_trie_projector_v1.py")
    StagePScopeGraphConstraintStateV1_1 = dfa.StagePScopeGraphConstraintStateV1_1
    StagePScopeGraphConstraintStateV1_2 = dfa_candidate.StagePScopeGraphConstraintStateV1_2
    StagePTokenTrieProjectorV1 = baseline_module.StagePTokenTrieProjectorV1
    StagePLivenessTokenTrieProjectorV1 = candidate_module.StagePLivenessTokenTrieProjectorV1

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in range(len(tokenizer))}
    excluded = set(tokenizer.all_special_ids) - {tokenizer.eos_token_id}
    baseline = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
                                         excluded_token_ids=excluded)
    candidate = StagePLivenessTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
                                                   excluded_token_ids=excluded)
    partial = json.loads(EVENT.read_text("utf-8"))["partial_output"]
    if not partial.endswith('"co'):
        raise RuntimeError("Run 2 heartbeat prefix drift")
    before_dead_token = partial[:-2]
    before_state = StagePScopeGraphConstraintStateV1_1().feed(before_dead_token)
    baseline_before = set(baseline.allowed_token_ids(before_state))
    candidate_before = set(candidate.allowed_token_ids(before_state))
    co_ids = {token_id for token_id, piece in pieces.items() if piece == "co"}
    committed_state = StagePScopeGraphConstraintStateV1_1().feed(partial)
    baseline_committed_empty = candidate_committed_empty = False
    try:
        baseline.allowed_token_ids(committed_state)
    except ValueError as exc:
        baseline_committed_empty = str(exc) == "EMPTY_ALLOWED_TOKEN_SET"
    try:
        candidate.allowed_token_ids(committed_state)
    except ValueError as exc:
        candidate_committed_empty = str(exc) == "EMPTY_ALLOWED_TOKEN_SET"
    coverage_prefix = partial[:-2] + 'coverage_decision":"'
    baseline_coverage = StagePScopeGraphConstraintStateV1_1().feed(coverage_prefix)
    candidate_coverage = StagePScopeGraphConstraintStateV1_2().feed(coverage_prefix)
    result = {
        "schema_name": "pastila-stage-p-scope-graph-liveness-real-tokenizer-characterization",
        "schema_version": "1.0.0-evaluation.1",
        "result": "PASS" if co_ids and co_ids <= baseline_before and candidate_before
                  and not baseline_committed_empty and not candidate_committed_empty
                  and baseline_coverage.choices == ("COMPLETE", "INDETERMINATE")
                  and candidate_coverage.choices == ("COMPLETE",) else "FAIL",
        "run2_partial_sha256": hashlib.sha256(partial.encode()).hexdigest(),
        "run2_partial_utf8_bytes": len(partial.encode()),
        "dead_token_piece": "co",
        "dead_token_ids": sorted(co_ids),
        "baseline_allowed_before_dead_token": len(baseline_before),
        "candidate_allowed_before_dead_token": len(candidate_before),
        "dead_token_allowed_by_baseline": bool(co_ids & baseline_before),
        "co_token_pruned_by_candidate": not bool(co_ids & candidate_before),
        "co_token_hypothesis_falsified": bool(co_ids & candidate_before),
        "committed_prefix_baseline_empty": baseline_committed_empty,
        "committed_prefix_candidate_empty": candidate_committed_empty,
        "baseline_coverage_choices": list(baseline_coverage.choices),
        "candidate_coverage_choices": list(candidate_coverage.choices),
        "tokenizer_vocabulary_size": len(tokenizer),
        "model_module_imported": any(name.startswith("peft") for name in sys.modules),
        "model_loads": 0,
        "model_calls": 0,
        "provider_calls": 0,
        "inference_calls": 0
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["result"] != "PASS" or result["model_module_imported"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
