from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import ConstructionObligationV2RunnerPreflightV1_1
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import bind_static_projector_preflight_v1_2
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_IDENTITY, EOS_TOKEN_ID, PROJECTOR_FREEZE_IDENTITY,
    TOKENIZER_IDENTITY, TokenPieceBundleV1,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import _fixture


SOURCE = Path("src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2.py")
ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runner-projector-preflight-v1-2.json")


def preflight():
    _, request = _fixture()
    bundle = TokenPieceBundleV1(
        MappingProxyType({2: "", 20: "{"}), frozenset((0, 1, 11)),
        EOS_TOKEN_ID, TOKENIZER_IDENTITY, DECODER_IDENTITY,
        PROJECTOR_FREEZE_IDENTITY)
    return ConstructionObligationV2RunnerPreflightV1_1(request, bundle)


def test_constructs_request_bound_projector_without_execution():
    result = bind_static_projector_preflight_v1_2(preflight=preflight())
    assert result.host_payload.source_context_identity == result.preflight.request.source_context_identity
    assert result.static_payload.payload_sha256 == result.host_payload.static_payload_sha256
    assert result.projector.allowed_token_ids([], lambda _: "").token_ids == (20,)


def test_cross_request_or_wrong_preflight_fails_closed():
    value = preflight()
    stale = replace(value, request=replace(value.request, source_context_identity="0" * 64))
    with pytest.raises(ValueError, match="HOST_BINDING_MISMATCH"):
        bind_static_projector_preflight_v1_2(preflight=stale)
    with pytest.raises(TypeError, match="PREFLIGHT_V1_1_REQUIRED"):
        bind_static_projector_preflight_v1_2(preflight=object())


def test_source_has_no_loading_launch_or_execution_surface():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not modules.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    text = SOURCE.read_text(encoding="utf-8")
    assert all(term not in text for term in ("from_pretrained", ".generate(", "if __name__", "main("))


def test_artifact_identity_and_authority():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    assert all(value is False for value in artifact["authority"].values())
