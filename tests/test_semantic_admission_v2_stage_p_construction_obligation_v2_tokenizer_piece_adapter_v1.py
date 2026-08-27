from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_IDENTITY, EOS_TOKEN_ID, PROJECTOR_FREEZE_IDENTITY,
    SPECIAL_TOKEN_IDS, TOKENIZER_IDENTITY, TOKENIZER_IMPLEMENTATION,
    TRANSFORMERS_VERSION, VOCABULARY_SIZE, TokenizerRuntimeIdentityV1,
    extract_identity_bound_token_pieces_v1,
)


class TokenizersBackend:
    eos_token_id = EOS_TOKEN_ID
    all_special_ids = tuple(sorted(SPECIAL_TOKEN_IDS))

    def __init__(self) -> None:
        self.decode_calls = 0

    def __len__(self) -> int:
        return VOCABULARY_SIZE

    def decode(self, token_ids, *, skip_special_tokens, clean_up_tokenization_spaces):
        self.decode_calls += 1
        assert skip_special_tokens is True
        assert clean_up_tokenization_spaces is False
        token_id = token_ids[0]
        return "" if token_id in SPECIAL_TOKEN_IDS else chr(0x20 + token_id % 90)


def identity() -> TokenizerRuntimeIdentityV1:
    return TokenizerRuntimeIdentityV1(
        TOKENIZER_IDENTITY, DECODER_IDENTITY, TRANSFORMERS_VERSION,
        TOKENIZER_IMPLEMENTATION, VOCABULARY_SIZE, EOS_TOKEN_ID,
        tuple(sorted(SPECIAL_TOKEN_IDS)), PROJECTOR_FREEZE_IDENTITY,
    )


@pytest.mark.parametrize("field,value", [
    ("tokenizer_identity", "sha256:" + "0" * 64),
    ("decoder_identity", "different"),
    ("transformers_version", "5.15.1"),
    ("tokenizer_implementation", "OtherBackend"),
    ("vocabulary_size", VOCABULARY_SIZE - 1),
    ("eos_token_id", 3),
    ("special_token_ids", (0, 1, 2)),
    ("projector_freeze_identity", "0" * 64),
])
def test_identity_mismatch_fails_before_decode(field, value):
    tokenizer = TokenizersBackend()
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        extract_identity_bound_token_pieces_v1(
            tokenizer=tokenizer, identity=replace(identity(), **{field: value}))
    assert tokenizer.decode_calls == 0


def test_extracts_complete_immutable_piece_bundle():
    tokenizer = TokenizersBackend()
    bundle = extract_identity_bound_token_pieces_v1(tokenizer=tokenizer, identity=identity())
    assert tokenizer.decode_calls == VOCABULARY_SIZE
    assert len(bundle.token_pieces) == VOCABULARY_SIZE
    assert bundle.excluded_token_ids == frozenset((0, 1, 11))
    assert bundle.eos_token_id == 2
    assert bundle.tokenizer_identity == TOKENIZER_IDENTITY
    with pytest.raises(TypeError):
        bundle.token_pieces[12] = "changed"


def test_module_is_launch_forbidden_and_has_no_runtime_imports():
    path = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not imported.intersection({"transformers", "torch", "peft", "subprocess"})
    assert not any(isinstance(node, ast.If) and isinstance(node.test, ast.Compare) for node in tree.body)
