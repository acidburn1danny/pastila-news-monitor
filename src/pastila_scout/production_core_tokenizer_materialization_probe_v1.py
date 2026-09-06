"""Offline probe for one content-addressed Production Core tokenizer materialization."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path

EXPECTED_FILES = (
    "chat_template.jinja",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
)
EXPECTED_FILE_SHA256 = {
    "chat_template.jinja": "2f545122222db8bb43ca0ea0c49e9185320a8670f7d35575b0da0eb48b1e8970",
    "config.json": "b1897778395bb1795489a048ebde2e6d216eee21014ce9c18193d15f097454a6",
    "tokenizer.json": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    "tokenizer_config.json": "f59f7294e4f26383d0ea93840fe21cf197784be0842a8301a0343e8c34ed0d6d",
}
CORPUS_SHA256 = "42d071e047bc7ea3a9cc2d1b7c2c22f74d8db4355a976c51cb727ee3dd0ecd78"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if (
        len(sys.argv) != 4
        or sys.argv[1] != "/tmp/tokenizer"
        or sys.argv[2] != "/tmp/corpus.json"
        or sys.argv[3] not in {"frozen-default", "fixed"}
    ):
        raise SystemExit("invalid tokenizer probe path")
    if os.environ != {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "LC_ALL": "C.UTF-8",
    }:
        raise SystemExit("invalid tokenizer probe environment")
    root = Path(sys.argv[1])
    if root.is_symlink() or tuple(sorted(item.name for item in root.iterdir())) != EXPECTED_FILES:
        raise SystemExit("invalid tokenizer closure")
    files = {name: _sha256(root / name) for name in EXPECTED_FILES}
    if files != EXPECTED_FILE_SHA256:
        raise SystemExit("tokenizer file identity mismatch")
    corpus_path = Path(sys.argv[2])
    corpus_bytes = corpus_path.read_bytes()
    if hashlib.sha256(corpus_bytes).hexdigest() != CORPUS_SHA256:
        raise SystemExit("comparison corpus identity mismatch")
    corpus = json.loads(corpus_bytes.decode("utf-8", errors="strict"))
    cases = corpus.get("cases")
    if (
        corpus.get("case_count") != 40
        or not isinstance(cases, list)
        or len(cases) != 40
        or len({case.get("case_id") for case in cases if isinstance(case, dict)}) != 40
        or any(
            not isinstance(case, dict)
            or not isinstance(case.get("text"), str)
            or not unicodedata.is_normalized("NFC", case["text"])
            for case in cases
        )
    ):
        raise SystemExit("comparison corpus invalid")
    from transformers import AutoTokenizer

    if sys.argv[3] == "fixed":
        tokenizer = AutoTokenizer.from_pretrained(
            root, local_files_only=True, fix_mistral_regex=True
        )
    else:
        tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True)
    case_tokens = {
        case["case_id"]: tokenizer.encode(case["text"], add_special_tokens=False)
        for case in cases
    }
    observation = {
        "schema": "pastila-production-core-tokenizer-materialization-probe",
        "schema_version": 1,
        "files": files,
        "corpus_sha256": CORPUS_SHA256,
        "mode": sys.argv[3],
        "tokenizer_class": type(tokenizer).__name__,
        "vocabulary_size": len(tokenizer),
        "case_tokens": case_tokens,
        "model_loaded": False,
        "inference_executed": False,
        "candidate_result_inspected": False,
        "network": "DENY_ALL_NEW_NAMESPACE",
    }
    encoded = json.dumps(
        observation, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    print(encoded.decode("utf-8"))
    print(hashlib.sha256(encoded).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
