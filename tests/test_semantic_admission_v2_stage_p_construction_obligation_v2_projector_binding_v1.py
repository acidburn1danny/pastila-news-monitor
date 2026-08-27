from __future__ import annotations

import ast
import base64
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import (
    DECODER_IDENTITY,
    PROJECTOR_FREEZE_IDENTITY,
    TOKENIZER_IDENTITY,
    bind_construction_obligation_v2_projector_v1,
    prepare_construction_obligation_v2_projector_binding_v1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_projector_binding_v1.py"


def _envelope(candidate: str = "Țară, știre — «nouă»"):
    return prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.encode(),
        factual_authority_utf8="Autoritatea confirmă știrea.".encode())


def test_static_binding_constructs_exact_frozen_projector_without_launch() -> None:
    envelope = _envelope()
    projector = bind_construction_obligation_v2_projector_v1(
        envelope=envelope, token_pieces={0: "", 1: "", 2: "", 11: "", 20: "{"})
    assert envelope.projector_freeze_identity == PROJECTOR_FREEZE_IDENTITY
    assert projector.tokenizer_identity == TOKENIZER_IDENTITY
    assert projector.decoder_identity == DECODER_IDENTITY
    assert projector.request_context_identity == envelope.source_context_identity
    assert projector.allowed_token_ids([], lambda _: "").token_ids == (20,)


def test_binding_is_deterministic_and_request_isolated() -> None:
    first = _envelope("prima cerere"); repeated = _envelope("prima cerere")
    second = _envelope("a doua cerere")
    assert first == repeated
    assert first.canonical_bytes() == repeated.canonical_bytes()
    assert first.source_context_identity != second.source_context_identity
    projector = bind_construction_obligation_v2_projector_v1(
        envelope=second, token_pieces={2: "", 20: "{"})
    assert projector.request_context_identity == second.source_context_identity


@pytest.mark.parametrize("field,value,error", [
    ("projector_freeze_identity", "0" * 64, "IDENTITY_MISMATCH"),
    ("tokenizer_identity", "sha256:" + "0" * 64, "IDENTITY_MISMATCH"),
    ("decoder_identity", "stale-decoder", "IDENTITY_MISMATCH"),
    ("source_context_identity", "0" * 64, "CONTEXT_IDENTITY_MISMATCH"),
])
def test_stale_or_conflicting_identity_fails_closed(field: str, value: str,
                                                    error: str) -> None:
    with pytest.raises(ValueError, match=error):
        bind_construction_obligation_v2_projector_v1(
            envelope=replace(_envelope(), **{field: value}),
            token_pieces={2: "", 20: "{"})


def test_malformed_or_source_unbound_input_fails_closed() -> None:
    envelope = _envelope()
    with pytest.raises(ValueError, match="SOURCE_BASE64_INVALID"):
        bind_construction_obligation_v2_projector_v1(
            envelope=replace(envelope, candidate_utf8_base64="%%%"),
            token_pieces={2: "", 20: "{"})
    tampered = base64.b64encode(b"different").decode()
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH"):
        bind_construction_obligation_v2_projector_v1(
            envelope=replace(envelope, candidate_utf8_base64=tampered),
            token_pieces={2: "", 20: "{"})
    with pytest.raises(ValueError, match="UTF8_BYTES_REQUIRED"):
        prepare_construction_obligation_v2_projector_binding_v1(
            candidate_utf8=b"", factual_authority_utf8=b"authority")


def test_module_has_no_execution_or_prompt_authority_imports() -> None:
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("subprocess", "transformers", "tokenizers", "provider", "executor",
                 "runner", "probe", "experimental_core", "prompt", "torch")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
