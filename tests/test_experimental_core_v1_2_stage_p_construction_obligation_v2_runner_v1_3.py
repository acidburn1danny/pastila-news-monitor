from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import ConstructionObligationV2RunnerPreflightV1_1
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import bind_static_projector_preflight_v1_2
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import bind_static_callback_preflight_v1_3
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import DECODER_IDENTITY, EOS_TOKEN_ID, PROJECTOR_FREEZE_IDENTITY, TOKENIZER_IDENTITY, TokenPieceBundleV1
from test_experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import preflight
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _valid_text


SOURCE = Path("src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3.py")
ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runner-callback-preflight-v1-3.json")


def callback_preflight(pieces=None):
    base = preflight()
    if pieces is not None:
        bundle = TokenPieceBundleV1(
            MappingProxyType(pieces), frozenset((0, 1, 11)), EOS_TOKEN_ID,
            TOKENIZER_IDENTITY, DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY)
        base = ConstructionObligationV2RunnerPreflightV1_1(base.request, bundle)
    return bind_static_callback_preflight_v1_3(
        projector_preflight=bind_static_projector_preflight_v1_2(preflight=base))


def test_prompt_prefix_is_sliced_and_initial_projection_is_deterministic():
    bound = callback_preflight({2: "", 20: "{"})
    first = bound.project_input_ids(
        input_token_ids=(900, 901), prompt_token_count=2,
        decode_generated=lambda ids: "" if not ids else "{")
    assert first.allowed_token_ids == (20,)
    second = bound.project_input_ids(
        input_token_ids=(700, 701, 20), prompt_token_count=2,
        decode_generated=lambda ids: "" if not ids else "{")
    assert second.projection_receipt.decoded_sha256 == hashlib.sha256(b"{").hexdigest()


def test_dead_state_produces_request_bound_no_legal_token_receipt():
    bound = callback_preflight({2: "", 20: "x"})
    decision = bound.project_input_ids(
        input_token_ids=(4, 5), prompt_token_count=2, decode_generated=lambda _: "")
    receipt = json.loads(decision.no_legal_token_receipt)
    assert decision.allowed_token_ids == ()
    assert receipt["provider_request_id"] == bound.projector_preflight.preflight.request.provider_request_id
    assert receipt["allowed_token_count"] == 0


def test_terminal_language_admits_only_eos_with_rebuild_equivalence():
    initial = preflight()
    initial_projector = bind_static_projector_preflight_v1_2(preflight=initial)
    text = _valid_text(initial_projector.projector.controller.tracker.context)
    character_ids = {character: token_id for token_id, character in enumerate(sorted(set(text)), 100)}
    pieces = {token_id: character for character, token_id in character_ids.items()}
    pieces[EOS_TOKEN_ID] = ""
    bundle = TokenPieceBundleV1(
        MappingProxyType(pieces), frozenset((0, 1, 11)), EOS_TOKEN_ID,
        TOKENIZER_IDENTITY, DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY)
    base = ConstructionObligationV2RunnerPreflightV1_1(initial.request, bundle)
    bound = bind_static_callback_preflight_v1_3(
        projector_preflight=bind_static_projector_preflight_v1_2(preflight=base))
    generated = tuple(character_ids[character] for character in text)
    decode = lambda ids: "".join(pieces[token_id] for token_id in ids)
    decision = bound.project_input_ids(
        input_token_ids=(800, 801, *generated), prompt_token_count=2,
        decode_generated=decode)
    assert decision.allowed_token_ids == (EOS_TOKEN_ID,)
    assert decision.projection_receipt.terminal is True
    assert decision.projection_receipt.eos_allowed is True
    assert decision.no_legal_token_receipt is None


def test_bad_slicing_and_cross_context_fail_closed():
    bound = callback_preflight()
    with pytest.raises(ValueError, match="SHORTER_THAN_PROMPT"):
        bound.project_input_ids(input_token_ids=(1,), prompt_token_count=2, decode_generated=lambda _: "")
    bound.projector_preflight.projector.request_context_identity = "0" * 64
    with pytest.raises(ValueError, match="CONTEXT_MISMATCH"):
        bind_static_callback_preflight_v1_3(
            projector_preflight=bound.projector_preflight)


def test_source_and_artifact_preserve_zero_execution_authority():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not modules.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    assert all(value is False for value in artifact["authority"].values())
