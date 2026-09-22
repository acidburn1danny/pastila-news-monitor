"""Tokenizer-only sequence/EOS audit for the published editorial bridge.

Run inside the frozen production rootfs. No model class or optimizer is loaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer

PREFIX = "editor-core-editorial-mechanics-bridge-v1"
EXPECTED_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_MANIFEST = "a4649f59a5a536c688e7d3741bc46e82d8997dc6a8c04948a25424528102ba3a"
EXPECTED_PLAN = "4caa3811ff1eb9e19bc0e460edd760755e224100953595e5a5c4b91ab73cb6ef"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def flat_manifest(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("model root")
    rows = []
    for path in sorted(root.iterdir(), key=lambda p: p.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("model materialization")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(block)
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + digest.digest())
    return sha(b"".join(rows))


def rows(artifacts: Path, label: str) -> list[dict]:
    return [json.loads(line) for line in (artifacts / f"{PREFIX}-{label}.jsonl").read_bytes().splitlines()]


def ids(value: object) -> list[int]:
    if hasattr(value, "get") and value.get("input_ids") is not None:
        value = value["input_ids"]
    value = getattr(value, "ids", value)
    if isinstance(value, (list, tuple)) and len(value) == 1 and hasattr(value[0], "ids"):
        value = value[0].ids
    if not isinstance(value, (list, tuple)) or not all(type(item) is int for item in value):
        raise ValueError("tokenizer output shape")
    return list(value)


def audit(model: Path, artifacts: Path) -> dict:
    manifest = json.loads((artifacts / f"{PREFIX}-manifest.json").read_bytes())
    plan = json.loads((artifacts / f"{PREFIX}-plan.json").read_bytes())
    if manifest["manifest_identity"] != EXPECTED_MANIFEST or plan["plan_identity"] != EXPECTED_PLAN:
        raise ValueError("published corpus identity")
    model_identity = flat_manifest(model)
    if model_identity != EXPECTED_MODEL:
        raise ValueError("base model materialization identity")
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.eos_token_id is None:
        raise ValueError("missing EOS")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    counts: dict[str, int] = {}
    maxima: dict[str, int] = {}
    eos_checks = 0
    ceiling = plan["factorial"]["common_runtime"]["max_sequence_tokens"]
    if ceiling != 3072:
        raise ValueError("sequence ceiling drift")
    for label in ("train-mechanics", "train-control", "train-mechanics-generic", "train-control-generic",
                  "replay-baseline", "replay-protective"):
        corpus = rows(artifacts, label)
        counts[label] = len(corpus)
        lengths = []
        for row in corpus:
            messages = row["messages"]
            if len(messages) != 3 or messages[-1]["role"] != "assistant":
                raise ValueError(f"training target shape: {label}")
            prefix = ids(tokenizer.apply_chat_template(messages[:2], tokenize=True, add_generation_prompt=True))
            full = ids(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False))
            if not full or full[-1] != tokenizer.eos_token_id or tokenizer.eos_token_id in full[len(prefix):-1]:
                raise ValueError(f"EOS closure: {label}:{row.get('example_id')}")
            lengths.append(len(full)); eos_checks += 1
        maxima[label] = max(lengths)
    for label in ("development", "holdout"):
        requests = rows(artifacts, f"{label}-requests")
        keys = {row["example_id"]: row for row in rows(artifacts, f"{label}-answer-key")}
        if len(keys) != len(requests):
            raise ValueError(f"answer key count: {label}")
        counts[label] = len(requests)
        lengths = []
        for row in requests:
            if len(row["messages"]) != 2:
                raise ValueError(f"evaluation target leak: {label}")
            messages = row["messages"]
            prefix = ids(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True))
            expected = keys[row["example_id"]]["assistant_target"]
            full = ids(tokenizer.apply_chat_template(messages + [{"role": "assistant", "content": expected}], tokenize=True, add_generation_prompt=False))
            if not full or full[-1] != tokenizer.eos_token_id or tokenizer.eos_token_id in full[len(prefix):-1]:
                raise ValueError(f"evaluation EOS closure: {label}:{row['example_id']}")
            lengths.append(len(full)); eos_checks += 1
        maxima[label] = max(lengths)
    maximum = max(maxima.values())
    if maximum > ceiling:
        raise ValueError(f"sequence ceiling exceeded: {maximum}>{ceiling}")
    core = {"schema": "editor-core-editorial-bridge-token-audit", "schema_version": 1,
            "manifest_identity": EXPECTED_MANIFEST, "plan_identity": EXPECTED_PLAN,
            "base_model_identity": model_identity, "tokenizer_file_sha256": sha((model / "tokenizer.json").read_bytes()),
            "tokenizer_config_sha256": sha((model / "tokenizer_config.json").read_bytes()),
            "chat_template_sha256": sha((model / "chat_template.jinja").read_bytes()),
            "tokenizer_fix_mistral_regex": True, "eos_token_id": tokenizer.eos_token_id,
            "sequence_ceiling": ceiling, "maximum_sequence_tokens": maximum,
            "maximum_by_partition": maxima, "row_counts": counts, "eos_checks": eos_checks,
            "model_loaded": False, "inference_performed": False, "optimizer_created": False,
            "optimizer_steps": 0, "training_performed": False}
    return {**core, "receipt_identity": sha(canonical(core))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("artifacts", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.model, args.artifacts), ensure_ascii=False, sort_keys=True))
