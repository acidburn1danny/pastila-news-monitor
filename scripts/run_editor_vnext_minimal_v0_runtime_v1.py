"""Minimal VNext V0 development runtime: SourcePacket -> R2 -> structure."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path, PurePosixPath

R2_LOCK_ID = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    temporary.replace(path)


def verify_identity(value: dict, key: str) -> None:
    core = {name: item for name, item in value.items() if name != key}
    if value.get(key) != digest_bytes(canonical(core)):
        raise ValueError(f"identity mismatch: {key}")


def verify_runtime_root(root: Path) -> tuple[dict, dict, dict]:
    lock = json.loads((root / "dependency-lock.json").read_text(encoding="utf-8")); verify_identity(lock, "lock_identity")
    if lock["r2_lock_identity"] != R2_LOCK_ID or lock["shadow_verifier"]["authority"] != "NON_AUTHORITATIVE_OPTIONAL":
        raise ValueError("runtime authority drift")
    expected = set()
    for item in lock["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("non-canonical runtime dependency path")
        path = root.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["size"] or digest_file(path) != item["sha256"]:
            raise ValueError(f"runtime dependency mismatch: {relative}")
        expected.add(relative.as_posix())
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "dependency-lock.json"}
    if actual != expected:
        raise ValueError("unlocked runtime dependency")
    contract = json.loads((root / "contract.json").read_text(encoding="utf-8")); verify_identity(contract, "contract_identity")
    platform = json.loads((root / "platform-requirements.json").read_text(encoding="utf-8"))
    if contract["contract_identity"] != lock["contract_identity"] or digest_file(root / "platform-requirements.json") != lock["platform_requirements_sha256"]:
        raise ValueError("contract/platform binding mismatch")
    return lock, contract, platform


def verify_source_packet(packet: dict, contract: dict) -> None:
    verify_identity(packet, "packet_identity")
    if packet.get("schema") != contract["source_packet"]["schema"] or packet.get("schema_version") != contract["source_packet"]["schema_version"]:
        raise ValueError("SourcePacket schema mismatch")
    spans = packet.get("spans")
    if not isinstance(spans, list) or not spans:
        raise ValueError("SourcePacket must contain spans")
    seen = set()
    for span in spans:
        if span["span_id"] in seen:
            raise ValueError("duplicate SourcePacket span")
        seen.add(span["span_id"])
        raw = span["text"].encode()
        if digest_bytes(raw) != span["sha256"] or raw[span["byte_start"]:span["byte_end"]] != raw:
            raise ValueError("SourcePacket byte binding failure")


def structural_output(raw: str, event_id: str) -> tuple[bool, str | None, str | None]:
    try:
        pairs = json.loads(raw, object_pairs_hook=lambda value: value)
        if not isinstance(pairs, list) or len({key for key, _ in pairs}) != len(pairs):
            raise ValueError("duplicate keys")
        value = dict(pairs)
        if set(value) != {"case_id", "text"} or value["case_id"] != event_id or not isinstance(value["text"], str) or not value["text"].strip():
            raise ValueError("schema or event binding")
        return True, value["text"].strip(), None
    except Exception as exc:
        return False, None, str(exc)


def safety_boundary(packet: dict, contract: dict) -> dict:
    sentences = [span["text"].strip() for span in packet["spans"] if span["text"].strip()]
    if len(sentences) <= contract["fallback"]["maximum_complete_source_sentences"]:
        return {"route": "SOURCE_PRESERVING_FALLBACK", "text": " ".join(sentences)}
    return {"route": "ABSTAIN", "text": None}


def optional_shadow(path: Path | None, source: str, raw: str, event_id: str) -> dict:
    if path is None:
        return {"status": "NOT_CONFIGURED_NON_BLOCKING", "authoritative": False}
    try:
        spec = importlib.util.spec_from_file_location("vnext_shadow", path)
        if spec is None or spec.loader is None: raise ValueError("shadow import unavailable")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        finding = module.verify(source, raw, event_id)
        return {"status": "OBSERVED_NON_BLOCKING", "authoritative": False, "plugin_sha256": digest_file(path), "receipt": finding}
    except Exception as exc:
        return {"status": "ERROR_NON_BLOCKING", "authoritative": False, "plugin_sha256": digest_file(path) if path.is_file() else None, "error": type(exc).__name__}


def verify_r2_closure(root: Path) -> dict:
    lock = json.loads((root / "dependency-lock.json").read_text(encoding="utf-8"))
    if lock.get("lock_identity") != R2_LOCK_ID:
        raise ValueError("R2 closure identity mismatch")
    tool = root / lock["layout"]["dependency_preflight"]
    spec = importlib.util.spec_from_file_location("r2_preflight", tool)
    if spec is None or spec.loader is None: raise ValueError("R2 preflight unavailable")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.verify(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True); parser.add_argument("--closure-root", type=Path, required=True)
    parser.add_argument("--source-packet", type=Path, required=True); parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--shadow-verifier", type=Path); parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    runtime_root, closure_root, output_root = args.runtime_root.resolve(), args.closure_root.resolve(), args.output_root.resolve()
    if output_root.exists(): raise ValueError("output root must be new")
    lock, contract, platform = verify_runtime_root(runtime_root)
    product_root = runtime_root.parents[1]
    expected_closure = (product_root / lock["r2_component_path"]).resolve()
    expected_platform = (product_root / lock["platform_component_path"]).resolve()
    if closure_root != expected_closure:
        raise ValueError("R2 closure must resolve inside the single VNext product root")
    packet = json.loads(args.source_packet.read_text(encoding="utf-8")); verify_source_packet(packet, contract)
    closure = verify_r2_closure(closure_root)
    preflight = {"status": "PASS_PREFLIGHT", "runtime_lock_identity": lock["lock_identity"], "contract_identity": contract["contract_identity"],
                 "r2_lock_identity": closure["lock_identity"], "source_packet_identity": packet["packet_identity"],
                 "shadow_required": False, "legacy_dependency_count": 0}
    if args.preflight_only:
        output_root.mkdir(parents=True); atomic(output_root / "terminal-receipt.json", {**preflight, "model_loaded": False, "inference_performed": False})
        print(json.dumps(preflight, sort_keys=True)); return

    import accelerate
    import bitsandbytes
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
    versions = {"python": sys.version.split()[0], "accelerate": accelerate.__version__, "bitsandbytes": bitsandbytes.__version__,
                "torch": torch.__version__, "transformers": sys.modules["transformers"].__version__, "peft": sys.modules["peft"].__version__}
    if versions["python"] != platform["python"] or torch.version.cuda != platform["cuda_runtime"]:
        raise ValueError("Python/CUDA platform mismatch")
    if Path(sys.prefix).resolve() != expected_platform:
        raise ValueError("Python runtime must resolve inside the single VNext product root")
    for key, expected in platform["packages"].items():
        if key in versions and versions[key] != expected: raise ValueError(f"platform version mismatch: {key}")
    prefix = str(Path(sys.prefix).resolve())
    for module in (accelerate, bitsandbytes, torch, sys.modules["transformers"], sys.modules["peft"]):
        if not str(Path(module.__file__).resolve()).startswith(prefix):
            raise ValueError(f"runtime import outside VNext platform: {module.__name__}")
    r2_lock = json.loads((closure_root / "dependency-lock.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(closure_root / r2_lock["layout"]["tokenizer"], local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token = tokenizer.eos_token
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base = AutoModelForImageTextToText.from_pretrained(closure_root / r2_lock["layout"]["base_model"], local_files_only=True, device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True, quantization_config=quant)
    if hasattr(base.model, "vision_tower"): base.model.vision_tower = None
    if hasattr(base.model, "multi_modal_projector"): base.model.multi_modal_projector = None
    model = PeftModel.from_pretrained(base, closure_root / r2_lock["layout"]["adapter"], is_trainable=False); model.eval()
    source = "\n".join(f"[{span['span_id']}] {span['text']}" for span in packet["spans"])
    user = contract["prompt"]["user_template"].replace("{event_id}", packet["event_id"]).replace("{sources}", source)
    messages = [{"role": "system", "content": contract["prompt"]["system"]}, {"role": "user", "content": user}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True); encoded = tokenizer(rendered, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        generated = model.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=contract["decoding"]["max_new_tokens"], eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True)
    raw = tokenizer.decode(generated[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
    valid, text, error = structural_output(raw, packet["event_id"]); safe = safety_boundary(packet, contract)
    output_root.mkdir(parents=True)
    if valid: atomic(output_root / "candidate.json", {"case_id": packet["event_id"], "text": text})
    shadow = optional_shadow(args.shadow_verifier, source, raw, packet["event_id"])
    result = {**preflight, "status": "PASS_V0_DEVELOPMENT_RUNTIME" if valid else "PASS_SAFE_BOUNDARY_ONLY", "structural_valid": valid,
              "structural_error": error, "candidate_sha256": digest_bytes(raw.encode()), "candidate_persisted": valid,
              "shadow": shadow, "shadow_affected_output": False, "production_acceptance_authority": False,
              "safety_boundary": {"route": safe["route"], "text_sha256": digest_bytes(safe["text"].encode()) if safe["text"] else None},
              "platform": versions, "model_loaded": True, "inference_performed": True, "training_performed": False, "optimizer_created": False}
    core = canonical(result); result["receipt_identity"] = digest_bytes(core); atomic(output_root / "terminal-receipt.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1"); main()
