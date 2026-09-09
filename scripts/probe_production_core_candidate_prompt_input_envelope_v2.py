"""Tokenizer-only envelope proof for the 200 exact Semantic Successor V2 requests."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
from pathlib import Path

TOKENIZER_SHA256 = "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
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


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def main() -> int:
    if len(sys.argv) != 8 or sys.argv[3] not in {"A", "B"}:
        raise SystemExit(
            "usage: probe REPOSITORY TOKENIZER MATERIALIZATION RUNTIME_SHA REPO_SHA LAUNCHER_SHA PROBE_SHA"
        )
    expected_environment = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "LC_ALL": "C.UTF-8",
        "EXPECTED_NETWORK_INTERFACES": "lo",
        "CUDA_VISIBLE_DEVICES": "",
    }
    if os.environ != expected_environment:
        raise SystemExit("probe environment mismatch")
    if [name for _, name in socket.if_nameindex()] != ["lo"]:
        raise SystemExit("network namespace mismatch")
    repository, tokenizer_root = map(Path, sys.argv[1:3])
    materialization, runtime_sha, repo_sha, launcher_sha, probe_sha = sys.argv[3:]
    if sha(Path(__file__).read_bytes()) != probe_sha:
        raise SystemExit("probe byte identity mismatch")
    manifest_bytes = (
        repository / "docs/artifacts/production-core-candidate-request-manifest-v2.json"
    ).read_bytes()
    manifest = json.loads(manifest_bytes)
    core = dict(manifest)
    manifest_identity = core.pop("request_manifest_identity", None)
    if (
        manifest_identity != sha(canonical(core))
        or manifest.get("request_count") != 200
    ):
        raise SystemExit("request manifest authority mismatch")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_root, local_files_only=True, fix_mistral_regex=True
    )
    rows = []
    for candidate, relative, expected in PROMPTS:
        system_bytes = (repository / relative).read_bytes()
        if sha(system_bytes) != expected:
            raise SystemExit("candidate system prompt mismatch")
        system_prompt = system_bytes.decode("utf-8", errors="strict")
        for request in manifest["requests"]:
            user_prompt = request["candidate_visible_request"]
            if sha(user_prompt.encode()) != request["candidate_visible_request_sha256"]:
                raise SystemExit("candidate-visible request mismatch")
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
            rows.append(
                {
                    "candidate_system_prompt_sha256": expected,
                    "case_id": request["case_id"],
                    "candidate_visible_request_sha256": request[
                        "candidate_visible_request_sha256"
                    ],
                    "input_tokens": int(encoded["input_ids"].shape[1]),
                }
            )
    if len(rows) != 400 or any(row["input_tokens"] > MAX_INPUT_TOKENS for row in rows):
        raise SystemExit("input token ceiling exceeded")
    maximum = max(row["input_tokens"] for row in rows)
    receipt_core = {
        "schema": "pastila-production-core-candidate-input-envelope-receipt",
        "schema_version": 2,
        "materialization": materialization,
        "request_manifest_identity": manifest_identity,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_load_semantics": "fix_mistral_regex=True",
        "runtime_closure_sha256": runtime_sha,
        "rootfs_sha256": "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
        "effective_tokenizer_sha256": "7a2235fbe0a3c0caf083a14fb7c9150828927dfb0dc8808abef4568b93bfff7d",
        "repository_snapshot_sha256": repo_sha,
        "launcher_sha256": launcher_sha,
        "probe_sha256": probe_sha,
        "candidate_system_prompt_sha256": [expected for _, _, expected in PROMPTS],
        "request_count": 200,
        "rendering_count": 400,
        "input_token_ceiling": MAX_INPUT_TOKENS,
        "maximum_input_tokens": maximum,
        "attaining_renderings": [
            [row["candidate_system_prompt_sha256"], row["case_id"]]
            for row in rows
            if row["input_tokens"] == maximum
        ],
        "token_count_root": sha(canonical(rows)),
        "model_loaded": False,
        "inference_executed": False,
        "candidate_execution_performed": False,
        "network": "DENY_ALL_NEW_NAMESPACE",
        "status": "PASS_ALL_RENDERINGS_WITHIN_1924_TOKENS",
    }
    receipt = {**receipt_core, "receipt_identity": sha(canonical(receipt_core))}
    print(canonical(receipt).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
