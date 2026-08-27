from __future__ import annotations

from dataclasses import replace

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_projector_binding_v1 import (
    StagePConstructionObligationProjectorEvaluatorInterfaceV1,
    StagePConstructionObligationProjectorRunnerInterfaceV1,
)


def _request():
    return {"factual_summary": "Autoritatea a publicat rezultatul.",
            "candidate": "Dosarul și-a pus cravată pentru fotografie."}


def test_evaluator_prepares_distinct_prompt_and_byte_bound_envelope(tmp_path, monkeypatch):
    class FakeRequest:
        def __init__(self, **kwargs): pass
        def render_prompt(self, request): return "unchanged governed prompt"
    monkeypatch.setattr(
        "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_request_candidate_v1.StagePConstructionObligationRequestCandidateV1",
        FakeRequest)
    interface = StagePConstructionObligationProjectorEvaluatorInterfaceV1(project_root=tmp_path)
    prepared = interface.prepare(_request())
    assert prepared.rendered_prompt == "unchanged governed prompt"
    assert prepared.source_binding.candidate_sha256
    assert prepared.source_binding.factual_authority_sha256
    assert _request()["candidate"].encode() not in prepared.source_binding.canonical_bytes()


def test_runner_reconstructs_context_and_projector_without_execution(tmp_path, monkeypatch):
    class FakeRequest:
        def __init__(self, **kwargs): pass
        def render_prompt(self, request): return "prompt"
    monkeypatch.setattr(
        "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_request_candidate_v1.StagePConstructionObligationRequestCandidateV1",
        FakeRequest)
    prepared = StagePConstructionObligationProjectorEvaluatorInterfaceV1(
        project_root=tmp_path).prepare(_request())
    projector = StagePConstructionObligationProjectorRunnerInterfaceV1.bind(
        envelope=prepared.source_binding, token_pieces={0: "{"}, eos_token_id=1,
        excluded_token_ids=())
    assert projector.allowed_token_ids([], lambda ids: "") == (0,)
    assert projector.controller.tracker.context.binding_identity == prepared.source_binding.context_identity


def test_runner_rejects_source_hash_and_context_tampering(tmp_path, monkeypatch):
    class FakeRequest:
        def __init__(self, **kwargs): pass
        def render_prompt(self, request): return "prompt"
    monkeypatch.setattr(
        "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_request_candidate_v1.StagePConstructionObligationRequestCandidateV1",
        FakeRequest)
    envelope = StagePConstructionObligationProjectorEvaluatorInterfaceV1(
        project_root=tmp_path).prepare(_request()).source_binding
    for changed in (replace(envelope, candidate_sha256="0" * 64),
                    replace(envelope, context_identity="0" * 64)):
        with pytest.raises(ValueError):
            StagePConstructionObligationProjectorRunnerInterfaceV1.bind(
                envelope=changed, token_pieces={0: "{"}, eos_token_id=1,
                excluded_token_ids=())


def test_evaluator_rejects_missing_or_non_string_sources(tmp_path, monkeypatch):
    class FakeRequest:
        def __init__(self, **kwargs): pass
    monkeypatch.setattr(
        "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_request_candidate_v1.StagePConstructionObligationRequestCandidateV1",
        FakeRequest)
    interface = StagePConstructionObligationProjectorEvaluatorInterfaceV1(project_root=tmp_path)
    for request in ({}, {"candidate": "x", "factual_summary": None}):
        with pytest.raises(ValueError): interface.prepare(request)
