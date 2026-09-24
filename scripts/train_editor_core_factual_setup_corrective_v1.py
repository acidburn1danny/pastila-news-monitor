"""Bound worker for EDITOR factual-setup corrective v1.

The fixture entry point validates the frozen experiment without importing an ML
runtime.  ``run_training`` is reachable only through the separately armed route.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from pathlib import Path

EXPECTED_ROWS = 72
EXPECTED_STEPS = 9
GRADIENT_ACCUMULATION = 8
EXPECTED_MANIFEST_IDENTITY = "50b387a0025025f5daac68cd65ab5570a731f9bb0db2a82c023921829e806a88"
EXPECTED_CONFIG_IDENTITY = "2b813d0485a3d3e186e4b5a4c88139af83d8d54fb25e759cee0921ee94da230b"
EXPECTED_CORPUS = "56c3e13cf79f24882c09b4b73403fa05c1ba628d48c58b822b09f440d848f606"
EXPECTED_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
EXPECTED_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def flat_manifest(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("materialization root mismatch")
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("materialization closure mismatch")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha_file(path)))
    if not rows:
        raise ValueError("materialization closure empty")
    return hashlib.sha256(b"".join(rows)).hexdigest()


def validate_config(config: dict[str, object], corpus_sha256: str, row_count: int) -> dict[str, object]:
    identity = config.get("config_identity")
    core = {key: value for key, value in config.items() if key != "config_identity"}
    if identity != EXPECTED_CONFIG_IDENTITY or identity != hashlib.sha256(canonical(core)).hexdigest():
        raise ValueError("config identity mismatch")
    expected = {
        "schema": "editor-factual-setup-corrective-config", "schema_version": 1,
        "contract_identity": "67a5cd5813d422c513795dd88b561db3f74a55ee2a932d8bcb2d0d1035eb0b37",
        "targeted_rows": 48, "replay_rows": 24, "holdout_rows": 24,
        "parent_adapter_sha256": EXPECTED_PARENT, "training_authorized": False,
        "voice_or_chief_objective": False,
    }
    if config != {**expected, "config_identity": EXPECTED_CONFIG_IDENTITY}:
        raise ValueError("frozen config mismatch")
    if corpus_sha256 != EXPECTED_CORPUS or row_count != EXPECTED_ROWS:
        raise ValueError("training corpus closure mismatch")
    order = list(range(row_count)); random.Random(314159).shuffle(order)
    return {
        "rows": row_count, "targeted_rows": 48, "replay_rows": 24,
        "gradient_accumulation_steps": GRADIENT_ACCUMULATION,
        "optimizer_steps": EXPECTED_STEPS, "checkpoint_steps": [EXPECTED_STEPS],
        "learning_rate": "0.0000005", "seed": 314159,
        "order_sha256": hashlib.sha256(canonical(order)).hexdigest(),
    }


def token_ids(value: object) -> list[int]:
    if hasattr(value, "get") and value.get("input_ids") is not None:
        value = value.get("input_ids")
    values = getattr(value, "ids", value)
    if isinstance(values, (list, tuple)) and len(values) == 1 and hasattr(values[0], "ids"):
        values = values[0].ids
    if not isinstance(values, (list, tuple)) or not all(type(item) is int for item in values):
        raise ValueError("tokenizer output shape mismatch")
    return list(values)


def save_checkpoint(output: Path, model: object, optimizer: object, torch: object, authority: dict[str, object]) -> str:
    temporary=output/'.checkpoint-000009.tmp'; final=output/'checkpoint-000009'
    if temporary.exists() or final.exists(): raise ValueError('checkpoint collision')
    temporary.mkdir(); model.save_pretrained(temporary/'adapter',safe_serialization=True)
    state=temporary/'training-state.pt'; torch.save({'optimizer_steps':EXPECTED_STEPS,'optimizer':optimizer.state_dict(),'cpu_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all()},state)
    core={**authority,'optimizer_steps':EXPECTED_STEPS,'state_sha256':sha_file(state)}; identity=hashlib.sha256(canonical(core)).hexdigest()
    (temporary/'checkpoint.json').write_text(json.dumps({**core,'checkpoint_identity':identity},sort_keys=True,indent=2)+'\n',encoding='utf-8')
    os.replace(temporary,final); return identity


def run_training(model_path: Path, parent_path: Path, corpus_path: Path, config_path: Path, output: Path) -> dict[str, object]:
    required = {"TRAINING_EXECUTION_AUTHORIZED", "MODEL_SHA256", "PARENT_SHA256", "CORPUS_SHA256", "CONFIG_IDENTITY", "MANIFEST_IDENTITY", "ROOTFS_SHA256", "LAUNCHER_SHA256", "WORKER_SHA256"}
    if any(not os.environ.get(name) for name in required) or os.environ["TRAINING_EXECUTION_AUTHORIZED"] != "1":
        raise ValueError("training execution authorization missing")
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise ValueError("training output must be distinct and empty")
    corpus_sha = sha_file(corpus_path)
    rows = [json.loads(line) for line in corpus_path.read_bytes().splitlines()]
    config = json.loads(config_path.read_bytes())
    plan = validate_config(config, corpus_sha, len(rows))
    if corpus_sha != os.environ["CORPUS_SHA256"] or os.environ["CONFIG_IDENTITY"] != EXPECTED_CONFIG_IDENTITY or os.environ["MANIFEST_IDENTITY"] != EXPECTED_MANIFEST_IDENTITY or sha_file(Path(__file__)) != os.environ["WORKER_SHA256"]:
        raise ValueError("source identity mismatch")
    model_identity, parent_identity = flat_manifest(model_path), flat_manifest(parent_path)
    if model_identity != EXPECTED_MODEL or parent_identity != EXPECTED_PARENT or model_identity != os.environ["MODEL_SHA256"] or parent_identity != os.environ["PARENT_SHA256"]:
        raise ValueError("model or parent identity mismatch")

    import bitsandbytes as bnb
    import torch
    from peft import PeftModel, prepare_model_for_kbit_training
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    seed = int(plan["seed"]); random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True); deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token = tokenizer.eos_token
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForImageTextToText.from_pretrained(model_path, local_files_only=True, quantization_config=quantization, device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True)
    model.model.vision_tower = None; model.model.multi_modal_projector = None
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": True})
    model = PeftModel.from_pretrained(model, parent_path, is_trainable=True); model.train()
    optimizer = bnb.optim.PagedAdamW8bit([p for p in model.parameters() if p.requires_grad], lr=float(plan["learning_rate"]), weight_decay=0.0)
    optimizer.zero_grad(set_to_none=True)
    order = list(range(len(rows))); random.Random(seed).shuffle(order); losses = []; steps = 0
    for position, index in enumerate(order, 1):
        messages = rows[index]["messages"]
        prefix = token_ids(tokenizer.apply_chat_template(messages[:2], tokenize=True, add_generation_prompt=True))
        tokens = token_ids(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False))
        if not tokens or tokens[-1] != tokenizer.eos_token_id or tokenizer.eos_token_id in tokens[len(prefix):-1] or len(tokens) > 3072:
            raise ValueError("token sequence closure mismatch")
        input_ids = torch.tensor([tokens], device="cuda"); labels = input_ids.clone(); labels[:, :len(prefix)] = -100
        loss = model(input_ids=input_ids, labels=labels, use_cache=False).loss
        (loss / GRADIENT_ACCUMULATION).backward(); losses.append(float(loss.detach().cpu()))
        if position % GRADIENT_ACCUMULATION == 0:
            optimizer.step(); torch.cuda.synchronize(); optimizer.zero_grad(set_to_none=True); steps += 1
    if steps != EXPECTED_STEPS: raise ValueError("optimizer schedule mismatch")
    authority={"manifest_identity":EXPECTED_MANIFEST_IDENTITY,"config_identity":EXPECTED_CONFIG_IDENTITY,"corpus_sha256":corpus_sha,"model_identity":model_identity,"parent_adapter_identity":parent_identity,"parent_checkpoint_identity":EXPECTED_CHECKPOINT,"rootfs_identity":os.environ['ROOTFS_SHA256'],"launcher_identity":os.environ['LAUNCHER_SHA256'],"worker_identity":os.environ['WORKER_SHA256']}
    checkpoint_identity=save_checkpoint(output,model,optimizer,torch,authority)
    model.save_pretrained(output / "adapter", safe_serialization=True)
    receipt = {"schema":"editor-factual-setup-corrective-v1-training-receipt","schema_version":1,**authority,"optimizer_steps":steps,"checkpoint_identity":checkpoint_identity,"final_loss":format(losses[-1],".17g"),"holdout_used":False,"voice_or_chief_objective":False,"promotion":False,"release":False}
    receipt["receipt_identity"] = hashlib.sha256(canonical(receipt)).hexdigest()
    (output / "training-receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def fixture_smoke(config: dict[str, object]) -> dict[str, object]:
    plan = validate_config(config, EXPECTED_CORPUS, EXPECTED_ROWS)
    core = {"schema":"editor-factual-setup-corrective-v1-worker-fixture-smoke","schema_version":1,"status":"PASS_FIXTURE_ONLY_ZERO_TRAINING",**plan,"model_loaded":False,"optimizer_created":False,"optimizer_steps_executed":0,"training_performed":False}
    return {**core, "smoke_identity": hashlib.sha256(canonical(core)).hexdigest()}


if __name__ == "__main__":
    if len(sys.argv) != 6: raise SystemExit("usage: worker MODEL PARENT CORPUS CONFIG OUTPUT")
    print(json.dumps(run_training(*map(Path, sys.argv[1:])), sort_keys=True, separators=(",", ":")))
