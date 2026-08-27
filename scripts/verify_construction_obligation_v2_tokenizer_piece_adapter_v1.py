"""Load only the frozen tokenizer and verify the V2 token-piece adapter."""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_IDENTITY,
    EOS_TOKEN_ID,
    PROJECTOR_FREEZE_IDENTITY,
    SPECIAL_TOKEN_IDS,
    TOKENIZER_IDENTITY,
    TOKENIZER_IMPLEMENTATION,
    TRANSFORMERS_VERSION,
    VOCABULARY_SIZE,
    TokenizerRuntimeIdentityV1,
    extract_identity_bound_token_pieces_v1,
)


MODEL = PurePosixPath(
    "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/"
    "huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/"
    "snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142"
)


def historical_tokenizer_identity(*, vocabulary_size: int) -> str:
    material = f"{MODEL}\n{vocabulary_size}".encode("utf-8")
    return "sha256:" + hashlib.sha256(material).hexdigest()


def main() -> None:
    from transformers import AutoTokenizer, __version__ as transformers_version

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    observed_vocabulary = len(tokenizer)
    observed_identity = historical_tokenizer_identity(
        vocabulary_size=observed_vocabulary)
    identity = TokenizerRuntimeIdentityV1(
        tokenizer_identity=observed_identity,
        decoder_identity=DECODER_IDENTITY,
        transformers_version=transformers_version,
        tokenizer_implementation=type(tokenizer).__name__,
        vocabulary_size=observed_vocabulary,
        eos_token_id=tokenizer.eos_token_id,
        special_token_ids=tuple(sorted(tokenizer.all_special_ids)),
        projector_freeze_identity=PROJECTOR_FREEZE_IDENTITY,
    )
    bundle = extract_identity_bound_token_pieces_v1(
        tokenizer=tokenizer, identity=identity)
    piece_digest = hashlib.sha256()
    for token_id, piece in bundle.token_pieces.items():
        piece_digest.update(str(token_id).encode("ascii"))
        piece_digest.update(b"\0")
        piece_digest.update(piece.encode("utf-8"))
        piece_digest.update(b"\n")
    receipt = {
        "artifact_type": "TOKENIZER_LOAD_ONLY_ADAPTER_VERIFICATION_RECEIPT",
        "result": "PASS",
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "tokenizer_identity": TOKENIZER_IDENTITY,
        "decoder_identity": DECODER_IDENTITY,
        "transformers_version": TRANSFORMERS_VERSION,
        "tokenizer_implementation": TOKENIZER_IMPLEMENTATION,
        "vocabulary_size": VOCABULARY_SIZE,
        "eos_token_id": EOS_TOKEN_ID,
        "special_token_ids": sorted(SPECIAL_TOKEN_IDS),
        "excluded_token_count": len(bundle.excluded_token_ids),
        "token_piece_sha256": piece_digest.hexdigest(),
        "activity": {
            "tokenizer_loads": 1,
            "model_loads": 0,
            "provider_calls": 0,
            "generation_or_inference_calls": 0,
            "runner_executor_or_probe_calls": 0,
            "stage_c_entries": 0
        }
    }
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
