"""Deterministic inference-only worker for the A1/A2 causal development pilot."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import unicodedata
from pathlib import Path

ROWS = 24
MAX_INPUT_TOKENS = 3072
MAX_NEW_TOKENS = 2048
RESPONSE_KEYS = ("schema", "schema_version", "case_id", "request_identity", "output_type",
                 "outcome", "text", "claim_bindings", "abstention_code")
ABSTENTION_CODES={"INSUFFICIENT_AUTHORITY","CONFLICTING_AUTHORITY","AMBIGUOUS_SCOPE",
                   "UNRESOLVED_REFERENCE","INSTRUCTION_AUTHORITY_CONFLICT",
                   "CANNOT_SATISFY_OUTPUT_CONTRACT","SAFETY_ENVELOPE_EXCEEDED"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def constraint_types():
    path=Path(__file__).with_name("editor_core_bridge_json_constraint_v3.py")
    spec=importlib.util.spec_from_file_location("editor_core_bridge_json_constraint_v3_bound",path)
    if spec is None or spec.loader is None: raise RuntimeError("constraint import")
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
    return module.BridgeJSONStateV3,module.BridgeTokenTrieV3


def flat_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("adapter/model closure")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha(path.read_bytes())))
    return sha(b"".join(rows))


def requests(path: Path) -> list[dict]:
    values = [json.loads(line) for line in path.read_bytes().splitlines()]
    if len(values) != ROWS or len({row.get("example_id") for row in values}) != ROWS:
        raise ValueError("development request inventory")
    for row in values:
        if row.get("split") != "DEVELOPMENT" or len(row.get("messages", [])) != 2:
            raise ValueError("development split")
        if any(message.get("role") == "assistant" for message in row["messages"]):
            raise ValueError("target leakage")
        payload = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
        if payload.get("case_id") != row["example_id"] or not str(payload.get("request_identity", "")).startswith("sha256:"):
            raise ValueError("request binding")
    return values


def validate_generated_response(text: str, payload: dict, terminal_eos: bool) -> dict:
    """Reject truncation, duplicate keys, malformed JSON and request substitution."""
    if not terminal_eos:
        raise ValueError("response missing terminal EOS")
    def object_without_duplicates(rows: list[tuple[str, object]]) -> dict:
        keys = [key for key, _ in rows]
        if len(set(keys)) != len(keys):
            raise ValueError("response duplicate key")
        return dict(rows)
    try:
        value = json.loads(text, object_pairs_hook=object_without_duplicates)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("response JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("response object")
    keys = tuple(value)
    if keys != RESPONSE_KEYS or len(set(keys)) != len(keys):
        raise ValueError("response key order/closure")
    if (value.get("schema") != "pastila-core-v2-structured-qualification-response"
            or value.get("schema_version") != 2
            or value.get("case_id") != payload["case_id"]
            or value.get("request_identity") != payload["request_identity"]
            or value.get("output_type") != payload["output_type"]
            or value.get("outcome") not in {"ANSWER", "ABSTAIN"}):
        raise ValueError("response request binding")
    if value["outcome"] == "ANSWER":
        if (not isinstance(value.get("text"), str) or not value["text"]
                or not isinstance(value.get("claim_bindings"), list)
                or value.get("abstention_code") is not None):
            raise ValueError("answer structure")
        bindings=value["claim_bindings"]
        allowed=[row["span_id"] for row in payload["authority_spans"]]
        positions={span:index for index,span in enumerate(allowed)}
        if not 1<=len(bindings)<=3: raise ValueError("binding count")
        seen=[]
        for expected,binding in enumerate(bindings,1):
            if (not isinstance(binding,dict) or tuple(binding)!=("claim_index","source_span_ids")
                    or binding.get("claim_index")!=expected): raise ValueError("binding structure")
            spans=binding.get("source_span_ids")
            if (not isinstance(spans,list) or not 1<=len(spans)<=8 or len(set(spans))!=len(spans)
                    or any(span not in positions for span in spans)
                    or [positions[span] for span in spans]!=sorted(positions[span] for span in spans)):
                raise ValueError("span binding")
            seen.extend(spans)
        if len(set(seen))!=len(seen) or len(seen)>24: raise ValueError("global span binding")
    elif (value.get("text") is not None or value.get("claim_bindings") != []
          or value.get("abstention_code") not in ABSTENTION_CODES):
        raise ValueError("abstention structure")
    return value


def persist_failure(output: Path, *, candidate: str, row: dict, payload: dict,
                    index: int, exc: Exception) -> dict:
    if any(output.iterdir()):
        raise ValueError("failure output not empty")
    core={"schema":"editor-core-bridge-causal-inference-failure","schema_version":1,
          "candidate":candidate,"case_id":row["example_id"],"request_identity":payload["request_identity"],
          "index":index,"failure_code":type(exc).__name__,"invalid_payload_persisted":False,
          "partial_response_rows_persisted":0,"receipt_persisted":False}
    failure={**core,"failure_identity":sha(canonical(core))}
    descriptor=os.open(output/"failure.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,"wb") as handle:
        handle.write(json.dumps(failure,sort_keys=True,indent=2).encode()+b"\n")
    return failure


def run(model: Path, adapter: Path, request_path: Path, output: Path, candidate: str) -> dict:
    if os.environ.get("BRIDGE_CAUSAL_INFERENCE_AUTHORIZED") != "1" or any(output.iterdir()):
        raise ValueError("inference invocation/output")
    if flat_manifest(model) != os.environ["MODEL_SHA256"] or flat_manifest(adapter) != os.environ["ADAPTER_SHA256"]:
        raise ValueError("model/adapter identity")
    if sha(request_path.read_bytes()) != os.environ["REQUESTS_SHA256"] or sha(Path(__file__).read_bytes()) != os.environ["WORKER_SHA256"]:
        raise ValueError("source identity")
    values = requests(request_path)

    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    loaded = AutoModelForImageTextToText.from_pretrained(
        model, local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
        device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = PeftModel.from_pretrained(loaded, adapter, is_trainable=False)
    loaded.eval()
    BridgeJSONStateV3,BridgeTokenTrieV3=constraint_types()
    token_pieces={item:tokenizer.decode([item],skip_special_tokens=True,clean_up_tokenization_spaces=False)
                  for item in range(len(tokenizer))}
    projector=BridgeTokenTrieV3(token_pieces=token_pieces,eos_token_id=tokenizer.eos_token_id,
                                excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    response_rows = []
    observations = []
    for index, row in enumerate(values, 1):
        payload = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
        encoded = tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        input_tokens = int(encoded["input_ids"].shape[1])
        if input_tokens > MAX_INPUT_TOKENS:
            raise ValueError("input token ceiling")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        def allowed(_batch_id, input_ids):
            decoded=tokenizer.decode(input_ids[input_tokens:].tolist(),skip_special_tokens=True,
                                     clean_up_tokenization_spaces=False)
            state=BridgeJSONStateV3.start(payload).feed(decoded)
            return list(projector.allowed_token_ids(state))
        try:
            with torch.inference_mode():
                generated = loaded.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=MAX_NEW_TOKENS,
                                            repetition_penalty=1.0, prefix_allowed_tokens_fn=allowed,
                                            eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True)
            tokens = generated[0, input_tokens:].cpu()
            text = tokenizer.decode(tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            if not text or unicodedata.normalize("NFC", text) != text:
                raise ValueError("empty/non-NFC response")
            terminal_eos = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
            validate_generated_response(text, payload, terminal_eos)
        except Exception as exc:
            persist_failure(output,candidate=candidate,row=row,payload=payload,index=index,exc=exc)
            raise
        response_rows.append({"case_id": row["example_id"], "request_identity": payload["request_identity"], "response": text})
        observations.append({"index": index, "case_id": row["example_id"], "request_identity": payload["request_identity"],
                             "input_tokens": input_tokens, "output_tokens": len(tokens),
                             "terminal_eos": terminal_eos,
                             "response_sha256": sha(text.encode())})
    response_bytes = b"".join(canonical(row) + b"\n" for row in response_rows)
    observation_bytes = b"".join(canonical(row) + b"\n" for row in observations)
    (output / "responses.jsonl").write_bytes(response_bytes)
    (output / "observations.jsonl").write_bytes(observation_bytes)
    core = {"schema": "editor-core-bridge-causal-development-inference-receipt", "schema_version": 1,
            "candidate": candidate, "rows": ROWS, "model_sha256": os.environ["MODEL_SHA256"],
            "adapter_sha256": os.environ["ADAPTER_SHA256"], "requests_sha256": os.environ["REQUESTS_SHA256"],
            "worker_sha256": os.environ["WORKER_SHA256"], "responses_sha256": sha(response_bytes),
            "observations_sha256": sha(observation_bytes), "terminal_eos": sum(row["terminal_eos"] for row in observations),
            "answer_key_accessed": False, "holdout_accessed": False, "network_activity": False,
            "training_performed": False, "optimizer_steps": 0}
    receipt = {**core, "receipt_identity": sha(canonical(core))}
    (output / "inference-receipt.json").write_bytes(json.dumps(receipt, sort_keys=True, indent=2).encode() + b"\n")
    return receipt


def fixture_smoke() -> dict:
    core = {"schema": "editor-core-bridge-causal-inference-fixture", "schema_version": 1,
            "model_loaded": False, "inference": False, "training": False, "optimizer_steps": 0}
    return {**core, "fixture_identity": sha(canonical(core))}


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit("usage: worker MODEL ADAPTER REQUESTS OUTPUT CANDIDATE")
    print(json.dumps(run(*(Path(value) for value in sys.argv[1:5]), sys.argv[5]), sort_keys=True))
