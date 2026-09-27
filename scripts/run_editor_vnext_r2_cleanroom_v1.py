"""Fail-closed clean-room startup and narrow R2 acceptance probe."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure-root", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--startup-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.closure_root).resolve()
    receipt = Path(args.receipt).resolve()
    if receipt.exists():
        raise ValueError("receipt must not already exist")
    lock = json.loads((root / "dependency-lock.json").read_text(encoding="utf-8"))
    if lock["lock_identity"] != "fe0754562970b9afe5a12ca03167c44e993182c6176ac06468d528f1973eda6d":
        raise ValueError("closure identity mismatch")
    expected_prefixes = (str(root), str(Path(sys.prefix).resolve()), "/usr/lib", "/usr/local/lib")
    imported_paths = []
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
    for module in (torch, sys.modules["peft"], sys.modules["transformers"]):
        module_path = str(Path(module.__file__).resolve())
        imported_paths.append(module_path)
        if not module_path.startswith(expected_prefixes):
            raise ValueError(f"undeclared import origin: {module_path}")
    model_path = root / lock["layout"]["base_model"]
    tokenizer_path = root / lock["layout"]["tokenizer"]
    adapter_path = root / lock["layout"]["adapter"]
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True, fix_mistral_regex=True)
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base = AutoModelForImageTextToText.from_pretrained(model_path, local_files_only=True, quantization_config=quant, device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, adapter_path, local_files_only=True)
    model.eval()
    result = {"schema":"editor-vnext-r2-cleanroom-receipt","schema_version":1,"status":"PASS_STARTUP","lock_identity":lock["lock_identity"],"python":sys.version.split()[0],"torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0),"import_origins":imported_paths,"legacy_dependency_count":0,"inference_performed":False}
    if not args.startup_only:
        system = (model_path / "SYSTEM_PROMPT.txt").read_text(encoding="utf-8")
        source = "SURSA: Primăria Alba Iulia a anunțat luni că podul va fi închis temporar între 3 și 5 octombrie pentru reparații. Instituția estimează costul lucrărilor la 2,4 milioane de lei și precizează că valoarea finală poate fi modificată după licitație."
        messages = [{"role":"system","content":system},{"role":"user","content":source}]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoded = tokenizer(rendered, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            output = model.generate(**encoded, do_sample=False, max_new_tokens=192, use_cache=True)
        text = tokenizer.decode(output[0, encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if not text or len(text) > 4000:
            raise ValueError("invalid acceptance output envelope")
        required = ("Alba Iulia", "3", "5", "2,4")
        if any(token not in text for token in required):
            raise ValueError("source-bound acceptance literals missing")
        result.update(status="PASS_R2_COMPONENT_E2E", inference_performed=True, output_sha256=hashlib.sha256(text.encode()).hexdigest(), output_chars=len(text))
    core = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    result["receipt_identity"] = hashlib.sha256(core).hexdigest()
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    main()
