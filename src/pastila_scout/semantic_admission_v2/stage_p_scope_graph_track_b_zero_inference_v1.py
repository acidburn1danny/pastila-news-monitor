"""Tokenizer/trie-only preflight for the Track-B prompt candidate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
PROMPT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-b-prompt-v1.txt"
CORE_PROMPT = ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"
CASE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence/stage-p-request.json"
PROMPT_IDENTITY = "35081f4840bce62317842cca75c42c143a62e04688867cbc1ae64b2e0db75cfc"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    raw = PROMPT.read_bytes()
    if not raw.endswith(b"\n") or hashlib.sha256(raw[:-1]).hexdigest() != PROMPT_IDENTITY:
        raise RuntimeError("Track-B prompt identity drift")
    template = raw[:-1].decode("utf-8")
    case = json.loads(CASE.read_text("utf-8"))
    rendered = template.replace("{candidate}", case["candidate"]).replace("{factual_summary}", case["factual_summary"])
    if rendered.index(case["candidate"]) >= rendered.index(case["factual_summary"]):
        raise RuntimeError("candidate-first render drift")

    package_root = ROOT / "src/pastila_scout"; semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    for module in ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
                   "stage_p_scope_graph_constraint_v1", "stage_p_scope_graph_constraint_v1_1"):
        _load(prefix + module, semantic_root / f"{module}.py")
    dfa = _load(prefix + "stage_p_scope_graph_constraint_v1_2", semantic_root / "stage_p_scope_graph_constraint_v1_2.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    projector_module = _load(prefix + "stage_p_liveness_trie_projector_v1",
                             semantic_root / "stage_p_liveness_trie_projector_v1.py")

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    batch = tokenizer.apply_chat_template(
        [{"role": "system", "content": CORE_PROMPT.read_text("utf-8")},
         {"role": "user", "content": rendered}], tokenize=True, add_generation_prompt=True,
        return_tensors="pt", return_dict=True)
    pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in range(len(tokenizer))}
    projector = projector_module.StagePLivenessTokenTrieProjectorV1(
        token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id})
    state = dfa.StagePScopeGraphConstraintStateV1_2()
    projector.prewarm((state,))
    allowed = projector.allowed_token_ids(state)
    result = {
        "schema_name": "pastila-stage-p-scope-graph-track-b-zero-inference-preflight",
        "schema_version": "1.0.0-evaluation.1", "result": "PASS",
        "prompt_identity": "sha256:" + PROMPT_IDENTITY, "candidate_first": True,
        "prompt_tokens": int(batch["input_ids"].shape[1]), "tokenizer_vocabulary_size": len(tokenizer),
        "trie_node_count": projector.trie_node_count, "initial_allowed_token_count": len(allowed),
        "transformers_tokenizer_loaded": True, "peft_imported": any(name.startswith("peft") for name in sys.modules),
        "model_loads": 0, "model_calls": 0, "provider_calls": 0, "inference_calls": 0,
        "case01_executed": False
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["peft_imported"] or not allowed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
