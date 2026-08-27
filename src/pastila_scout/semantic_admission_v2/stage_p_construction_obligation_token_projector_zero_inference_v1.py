"""Real-tokenizer, zero-inference equivalence for the V2 projector candidate."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"


def main() -> None:
    started = time.perf_counter(); sys.path.insert(0, str(ROOT / "tests"))
    if "pytest" not in sys.modules:
        stub = types.ModuleType("pytest")
        stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda f: f))
        stub.raises = lambda *a, **k: None; sys.modules["pytest"] = stub
    from transformers import AutoTokenizer
    from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context, _valid_text
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_token_projector_v1 import StagePConstructionObligationTokenProjectorV1
    from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    identity = "sha256:" + hashlib.sha256(f"{MODEL}\n{len(tokenizer)}".encode()).hexdigest()
    if identity != TOKENIZER_IDENTITY: raise SystemExit("TOKENIZER_IDENTITY_MISMATCH")
    decode = lambda ids: tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    pieces = {item: decode([item]) for item in range(len(tokenizer))}
    excluded = (set(tokenizer.all_special_ids) - {tokenizer.eos_token_id}) | {item for item, piece in pieces.items() if not piece}
    context, _, _ = _case_context(); raw = _valid_text(context)
    controller = StagePConstructionObligationCharacterControllerV1(context=context, decoder_identity=DECODER_IDENTITY)
    projector = StagePConstructionObligationTokenProjectorV1(
        controller=controller, token_pieces=pieces, eos_token_id=tokenizer.eos_token_id,
        tokenizer_identity=TOKENIZER_IDENTITY, decoder_identity=DECODER_IDENTITY,
        excluded_token_ids=excluded)
    positions = {"INITIAL": 0, "LITERAL": 1,
        "CHOICE": raw.index('"overall_disposition":"') + len('"overall_disposition":"'),
        "STRING": raw.index('"role_basis":"') + len('"role_basis":"'),
        "V2_REFERENCE": raw.index('"candidate_span_ref":') + len('"candidate_span_ref":'),
        "AFTER_ENTRY": raw.index('},{"entry_id":"P2"') + 1, "TERMINAL": len(raw)}
    rows = []; exact = True
    for name, position in positions.items():
        prefix = raw[:position]; ids = tokenizer.encode(prefix, add_special_tokens=False)
        state = controller.tracker.state_for(ids, decode).state
        oracle = []
        if state.terminal: oracle = [tokenizer.eos_token_id]
        else:
            for token_id, piece in pieces.items():
                if token_id in excluded or token_id == tokenizer.eos_token_id: continue
                try: state.feed(piece); oracle.append(token_id)
                except StagePRoleCoherenceConstraintViolationV1: pass
        before = time.perf_counter(); result = projector.project(ids, decode); elapsed = time.perf_counter() - before
        equal = result.allowed_token_ids == tuple(sorted(oracle)); exact = exact and equal
        rows.append({"state": name, "sets_equal": equal, "allowed_token_count": len(result.allowed_token_ids),
                     "receipt_liveness": result.receipt.liveness, "seconds": round(elapsed, 6)})
    output = {"schema_name":"pastila-semantic-admission-v2-stage-p-construction-obligation-token-projector-zero-inference",
        "schema_version":"1.0.0-evaluation.1", "result":"PASS" if exact else "FAIL",
        "tokenizer_identity":TOKENIZER_IDENTITY,"vocabulary_size":len(tokenizer),"rows":rows,
        "trie_node_count":projector.trie_node_count,"cache_size":projector.cache_size,
        "elapsed_seconds":round(time.perf_counter()-started,6),
        "environment":{"python":platform.python_version(),"pydantic":__import__("pydantic").__version__},
        "activity":{"tokenizer_loads":1,"projector_objects":1,"model_loads":0,"model_calls":0,
                    "provider_calls":0,"inference_calls":0,"evaluator_objects":0,"runner_objects":0,
                    "probe_constructions":0,"probe_executions":0}}
    print(json.dumps(output,sort_keys=True,separators=(",",":")))
    if not exact: raise SystemExit(1)


if __name__ == "__main__": main()
