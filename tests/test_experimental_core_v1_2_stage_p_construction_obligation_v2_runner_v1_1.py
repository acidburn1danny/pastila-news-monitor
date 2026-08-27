from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import (
    ConstructionObligationV2RunnerPreflightV1_1,
    bind_injected_tokenizer_preflight_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import RunnerRequestV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_IDENTITY, EOS_TOKEN_ID, PROJECTOR_FREEZE_IDENTITY,
    SPECIAL_TOKEN_IDS, TOKENIZER_IDENTITY, TOKENIZER_IMPLEMENTATION,
    TRANSFORMERS_VERSION, VOCABULARY_SIZE, TokenizerRuntimeIdentityV1,
)


SOURCE = Path("src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1.py")
ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runner-tokenizer-preflight-v1-1.json")


class TokenizersBackend:
    eos_token_id = EOS_TOKEN_ID
    all_special_ids = tuple(sorted(SPECIAL_TOKEN_IDS))

    def __init__(self): self.decode_calls = 0
    def __len__(self): return VOCABULARY_SIZE
    def decode(self, ids, *, skip_special_tokens, clean_up_tokenization_spaces):
        self.decode_calls += 1
        return "" if ids[0] in SPECIAL_TOKEN_IDS else "x"


def request():
    return RunnerRequestV1("provider-request", "source-context", "a" * 64, b"{}\n", 100)


def identity():
    return TokenizerRuntimeIdentityV1(
        TOKENIZER_IDENTITY, DECODER_IDENTITY, TRANSFORMERS_VERSION,
        TOKENIZER_IMPLEMENTATION, VOCABULARY_SIZE, EOS_TOKEN_ID,
        tuple(sorted(SPECIAL_TOKEN_IDS)), PROJECTOR_FREEZE_IDENTITY)


def test_static_preflight_binds_validated_request_to_immutable_piece_bundle():
    tokenizer = TokenizersBackend()
    result = bind_injected_tokenizer_preflight_v1_1(
        validated_request=request(), tokenizer=tokenizer,
        tokenizer_runtime_identity=identity())
    assert type(result) is ConstructionObligationV2RunnerPreflightV1_1
    assert result.request.source_context_identity == "source-context"
    assert len(result.token_piece_bundle.token_pieces) == VOCABULARY_SIZE
    assert tokenizer.decode_calls == VOCABULARY_SIZE


def test_bad_request_or_identity_fails_before_decode():
    tokenizer = TokenizersBackend()
    with pytest.raises(TypeError, match="VALIDATED_RUNNER_REQUEST_REQUIRED"):
        bind_injected_tokenizer_preflight_v1_1(
            validated_request=object(), tokenizer=tokenizer,
            tokenizer_runtime_identity=identity())
    assert tokenizer.decode_calls == 0
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        bind_injected_tokenizer_preflight_v1_1(
            validated_request=request(), tokenizer=tokenizer,
            tokenizer_runtime_identity=replace(identity(), decoder_identity="wrong"))
    assert tokenizer.decode_calls == 0


def test_source_is_passive_and_launch_forbidden():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    modules = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not modules.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    text = SOURCE.read_text(encoding="utf-8")
    assert all(term not in text for term in ("from_pretrained", ".generate(", "if __name__", "main("))


def test_artifact_identity_and_authority_are_fail_closed():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    assert all(value is False for value in artifact["authority"].values())
