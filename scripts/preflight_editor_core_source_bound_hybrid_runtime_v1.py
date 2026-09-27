"""Executable exact-tokenizer zero-step for the hybrid feasibility boundary."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from editor_core_source_bound_hybrid_runtime_v1 import ARMS, SEEDS, canonical, flat_directory_identity, sha
from fixture_editor_core_source_bound_hybrid_feasibility_v1 import validate_ledger

SOURCE_COMMIT = "50c103a5cf7238588789ed3600693ff4ac2ba053"
SOURCE_TREE = "8687172d3ba0769d4fc2fe70212ca7f28423b2cd"
PACK_IDENTITY = "bbad139fde613c1c912cd53992b4c2be047d73180f6a6ae732dc6348461d28f9"
PROTOCOL_IDENTITY = "5a5ef79af85a3b58b3c0e2f46be3f9e3dd573d75dae361c6d6df88588f7c1aea"
TOKENIZER_SHA256 = "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135"
PARENT_ADAPTER_IDENTITY = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
PREFIX = "editor-core-source-bound-hybrid-feasibility-v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--parent-adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and (args.output.is_symlink() or any(args.output.iterdir())):
        raise ValueError("zero-step output root must be new or empty")

    tree = subprocess.check_output(["git", "show", "-s", "--format=%T", SOURCE_COMMIT], text=True).strip()
    if tree != SOURCE_TREE:
        raise ValueError("published source tree mismatch")
    manifest = json.loads((args.artifact_root / f"{PREFIX}-manifest.json").read_text(encoding="utf-8"))
    protocol = json.loads((args.artifact_root / f"{PREFIX}-protocol.json").read_text(encoding="utf-8"))
    if manifest["pack_identity"] != PACK_IDENTITY or protocol["protocol_identity"] != PROTOCOL_IDENTITY:
        raise ValueError("pack/protocol identity mismatch")
    if manifest["files"] != {name: sha((args.artifact_root / name).read_bytes()) for name in manifest["files"]}:
        raise ValueError("manifest closure mismatch")
    if not protocol["fixture_selection_uses_oracle"] or protocol["autonomous_ledger_construction_claimed"]:
        raise ValueError("oracle feasibility limitation drift")
    if protocol["parent"] != "R2_STEP_9" or protocol["successor_training"] != "SUSPENDED":
        raise ValueError("parent/training boundary drift")

    tokenizer_json = args.tokenizer_dir / "tokenizer.json"
    if sha(tokenizer_json.read_bytes()) != TOKENIZER_SHA256:
        raise ValueError("tokenizer identity mismatch")
    if flat_directory_identity(args.parent_adapter) != PARENT_ADAPTER_IDENTITY:
        raise ValueError("R2 adapter identity mismatch")

    from tokenizers import Tokenizer  # tokenizer load only; no model import or load

    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    ledgers = read_jsonl(args.artifact_root / f"{PREFIX}-ledgers.jsonl")
    if len(ledgers) != 48:
        raise ValueError("ledger inventory mismatch")
    encoded_rows = 0
    token_count = 0
    for ledger in ledgers:
        validate_ledger(ledger)
        texts = [ledger["request"]] + [
            atom["quote"] for atom in ledger["atoms"] if atom["atom_id"] in ledger["extractive_fallback"]["atom_ids"]
        ]
        for text in texts:
            ids = tokenizer.encode(text, add_special_tokens=False).ids
            if not ids:
                raise ValueError("empty exact-tokenizer mapping")
            encoded_rows += 1
            token_count += len(ids)

    slots = [
        {
            "slot_id": f"{arm}__seed_{seed}",
            "arm": arm,
            "seed": seed,
            "ledgers_validated": 48,
            "output_root_required_distinct_and_empty": True,
        }
        for arm in ARMS for seed in SEEDS
    ]
    core = {
        "schema": "editor-source-bound-hybrid-runtime-zero-step",
        "schema_version": 1,
        "status": "PASS_9_ZERO_STEP",
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "pack_identity": PACK_IDENTITY,
        "protocol_identity": PROTOCOL_IDENTITY,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "parent": "R2_STEP_9",
        "parent_adapter_identity": PARENT_ADAPTER_IDENTITY,
        "slots": slots,
        "encoded_texts": encoded_rows,
        "token_count": token_count,
        "oracle_fixture_upper_bound": True,
        "autonomous_ledger_construction_claimed": False,
        "model_loaded": False,
        "inference_performed": False,
        "optimizer_created": False,
        "training_performed": False,
        "historical_holdouts_read": False,
        "parent_selection_authority": False,
    }
    receipt = {**core, "receipt_identity": sha(canonical(core))}
    args.output.mkdir(parents=True, exist_ok=True)
    temporary = args.output / "zero-step.json.tmp"
    temporary.write_bytes((json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    temporary.replace(args.output / "zero-step.json")
    print(json.dumps({
        "status": core["status"], "slots": len(slots), "encoded_texts": encoded_rows,
        "token_count": token_count, "receipt_identity": receipt["receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
