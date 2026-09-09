"""Tokenizer-only proof that every frozen candidate request fits the input envelope."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
from pathlib import Path

TOKENIZER_SHA256 = "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
CORPUS_IDENTITY = "5933f6ddb450a00566cb42a7dabd908975687360e5d9f16766d55b1dff7899b6"
MAX_INPUT_TOKENS = 1924
PROMPTS = (
    (
        "pastila-editor-core-v1.1-experimental",
        ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt",
        "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
    ),
    (
        "pastila-editor-core-v1.2-experimental",
        ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
        "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
    ),
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 9 or sys.argv[3] not in {"A", "B"}:
        raise SystemExit("usage: probe REPOSITORY TOKENIZER MATERIALIZATION ROOTFS BASE_TOKENIZER EFFECTIVE_TOKENIZER LAUNCHER PROBE")
    if os.environ != {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "PYTHONPATH": "/tmp/repo/src",
        "LC_ALL": "C.UTF-8",
        "EXPECTED_NETWORK_INTERFACES": "lo",
        "CUDA_VISIBLE_DEVICES": "",
    }:
        raise SystemExit("probe environment mismatch")
    if [name for _, name in socket.if_nameindex()] != ["lo"]:
        raise SystemExit("network namespace contains unexpected interfaces")
    repository, tokenizer_root = map(Path, sys.argv[1:3])
    materialization = sys.argv[3]
    rootfs_sha256, tokenizer_sha256, effective_tokenizer_sha256, launcher_sha256, probe_sha256 = sys.argv[4:]
    if (
        rootfs_sha256 != "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
        or tokenizer_sha256 != TOKENIZER_SHA256
        or _sha(Path(__file__).read_bytes()) != probe_sha256
        or any(len(value) != 64 for value in (effective_tokenizer_sha256, launcher_sha256, probe_sha256))
    ):
        raise SystemExit("runtime identity mismatch")
    sys.path.insert(0, str(repository / "src"))
    from pastila_scout.production_core_candidate_qualification_v1 import (
        SYSTEM_INSTRUCTION,
        build_candidate_prompt,
        canonical_json_bytes,
    )

    corpus_bytes = (
        repository / "docs/artifacts/production-core-qualification-corpus-v1.json"
    ).read_bytes()
    corpus = json.loads(corpus_bytes)
    if corpus.get("corpus_identity") != CORPUS_IDENTITY:
        raise SystemExit("corpus identity mismatch")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_root, local_files_only=True, fix_mistral_regex=True
    )
    rows = []
    for candidate, relative, expected in PROMPTS:
        system_bytes = (repository / relative).read_bytes()
        if _sha(system_bytes) != expected:
            raise SystemExit("candidate system prompt identity mismatch")
        system_prompt = system_bytes.decode("utf-8", errors="strict")
        for case in corpus["cases"]:
            user_prompt = build_candidate_prompt(case)
            encoded = tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            input_tokens = int(encoded["input_ids"].shape[1])
            rows.append(
                {
                    "candidate": candidate,
                    "case_id": case["case_id"],
                    "request_sha256": _sha(user_prompt.encode("utf-8")),
                    "input_tokens": input_tokens,
                }
            )
    if len(rows) != 400 or any(row["input_tokens"] > MAX_INPUT_TOKENS for row in rows):
        raise SystemExit("input token ceiling exceeded")
    maximum = max(row["input_tokens"] for row in rows)
    receipt_core = {
        "schema": "pastila-production-core-candidate-prompt-input-envelope-receipt",
        "schema_version": 1,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "rootfs_sha256": rootfs_sha256,
        "launcher_sha256": launcher_sha256,
        "probe_sha256": probe_sha256,
        "consumed_tokenizer_snapshot_sha256": tokenizer_sha256,
        "effective_runner_tokenizer_closure_sha256": effective_tokenizer_sha256,
        "production_model_tokenizer_equivalence": "EXACT_FIVE_FILE_CANONICAL_TAR_SHA256",
        "tokenizer_load_semantics": "fix_mistral_regex=True",
        "materialization": materialization,
        "corpus_identity": CORPUS_IDENTITY,
        "common_instruction_sha256": _sha(SYSTEM_INSTRUCTION.encode("utf-8")),
        "candidate_system_prompt_sha256": {
            candidate: expected for candidate, _, expected in PROMPTS
        },
        "request_count": len(rows),
        "input_token_ceiling": MAX_INPUT_TOKENS,
        "maximum_input_tokens": maximum,
        "attaining_requests": [
            [row["candidate"], row["case_id"]]
            for row in rows
            if row["input_tokens"] == maximum
        ],
        "request_token_count_root": _sha(canonical_json_bytes(rows)),
        "model_loaded": False,
        "inference_executed": False,
        "network": "DENY_ALL_NEW_NAMESPACE",
        "status": "PASS_ALL_EXACT_REQUESTS_WITHIN_FROZEN_INPUT_ENVELOPE",
    }
    receipt = {**receipt_core, "receipt_identity": _sha(canonical_json_bytes(receipt_core))}
    print(canonical_json_bytes(receipt).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
