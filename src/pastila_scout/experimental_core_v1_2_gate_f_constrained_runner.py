"""WSL-side evaluation-only Core V1.2 runner with Gate-F constrained decoding."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ADAPTER = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-2-deontology-20260820-003/checkpoint-final/adapter")
ROOT = Path("/mnt/c/Projects/pastila-news-monitor")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _constraint_types():
    dfa = _load("sav2_gate_f_dfa_frozen", ROOT / "src/pastila_scout/semantic_admission_v2/gate_f_constraint_v1.py")
    optimized = _load("sav2_gate_f_trie_frozen", ROOT / "src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py")
    return dfa.GateFConstraintStateV1, optimized.GateFTokenTrieProjectorOptimizedV1


def _build_projector(tokenizer):
    State, Trie = _constraint_types()
    token_pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in range(len(tokenizer))}
    projector = Trie(
        token_pieces=token_pieces,
        eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id},
    )
    prefixes = (
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"',
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":null,"authority_support":"',
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":null,"authority_support":null,"unsupported_proposition":"',
    )
    started = time.perf_counter()
    projector.prewarm(State().feed(prefix) for prefix in prefixes)
    return State, projector, time.perf_counter() - started


def preflight(target: Path) -> None:
    from transformers import AutoTokenizer, PrefixConstrainedLogitsProcessor

    lifecycle = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-constrained-runner-preflight",
        "schema_version": "1.0.0",
        "tokenizer_load_started": True,
        "tokenizer_load_succeeded": False,
        "trie_build_succeeded": False,
        "prewarm_succeeded": False,
        "model_imported": False,
        "model_load_started": False,
        "model_loaded": False,
        "generation_started": False,
        "model_calls": 0,
        "provider_calls": 0,
    }
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    lifecycle["tokenizer_load_succeeded"] = True
    State, projector, prewarm_seconds = _build_projector(tokenizer)
    lifecycle.update(trie_build_succeeded=True, prewarm_succeeded=True)
    samples = (
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}',
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"INDETERMINATE","reason_records":[{"code":"ADMISSION_INDETERMINATE","status":"DECISIVE","candidate_span":null,"authority_support":null,"unsupported_proposition":"x","confidence":0.5}]}',
    )
    lifecycle.update(
        native_prefix_constraint_available=PrefixConstrainedLogitsProcessor is not None,
        trie_node_count=projector.trie_node_count,
        prewarm_seconds=round(prewarm_seconds, 6),
        canonical_streams_terminal=all(State().feed(item).can_eos for item in samples),
        root_fence_impossible=all(not tokenizer.decode([item], skip_special_tokens=True).startswith("```") for item in projector.allowed_token_ids(State())),
        terminal_only_eos=projector.allowed_token_ids(State().feed(samples[0])) == (tokenizer.eos_token_id,),
        result="PASS",
    )
    target.write_text(json.dumps(lifecycle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(request_path: Path, response_path: Path, prompt_path: Path, lifecycle_path: Path) -> None:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    lifecycle = {"inference_started": False, "inference_succeeded": False, "model_load_started": False, "model_load_succeeded": False, "constraint_active": True}
    _write(lifecycle_path, lifecycle)
    request = json.loads(request_path.read_text("utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    State, projector, prewarm_seconds = _build_projector(tokenizer)
    lifecycle.update(constraint_prewarm_succeeded=True, constraint_prewarm_seconds=prewarm_seconds, trie_node_count=projector.trie_node_count)
    _write(lifecycle_path, lifecycle)
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    lifecycle["model_load_started"] = True; _write(lifecycle_path, lifecycle)
    model = AutoModelForImageTextToText.from_pretrained(MODEL, local_files_only=True, quantization_config=quantization, device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True)
    model.model.vision_tower = None; model.model.multi_modal_projector = None
    model = PeftModel.from_pretrained(model, ADAPTER, is_trainable=False); model.eval()
    lifecycle["model_load_succeeded"] = True; _write(lifecycle_path, lifecycle)
    batch = tokenizer.apply_chat_template([{"role": "system", "content": prompt_path.read_text("utf-8")}, {"role": "user", "content": request["prompt"]}], tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True)
    prompt_tokens = int(batch["input_ids"].shape[1])
    batch = {name: value.to("cuda") for name, value in batch.items()}

    def allowed(_batch_id, input_ids):
        generated = input_ids[prompt_tokens:].tolist()
        decoded = tokenizer.decode(generated, skip_special_tokens=True)
        state = State().feed(decoded)
        return list(projector.allowed_token_ids(state))

    lifecycle["inference_started"] = True; _write(lifecycle_path, lifecycle)
    with torch.inference_mode():
        generated = model.generate(**batch, do_sample=False, num_beams=1, repetition_penalty=1.0, max_new_tokens=int(request["max_new_tokens"]), eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True, prefix_allowed_tokens_fn=allowed)
    tokens = generated[0, prompt_tokens:].cpu()
    lifecycle["inference_succeeded"] = True; _write(lifecycle_path, lifecycle)
    response_path.write_bytes(_canonical({
        "output": tokenizer.decode(tokens, skip_special_tokens=True),
        "terminal_eos": bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id),
        "constraint_active": True,
    }))


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--preflight-only":
        preflight(Path(sys.argv[2]))
    elif len(sys.argv) == 5:
        run(*map(Path, sys.argv[1:5]))
    else:
        raise SystemExit("invalid constrained runner arguments")
