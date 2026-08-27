from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_projector_binding_v1 import StagePConstructionObligationProjectorEvaluatorInterfaceV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_projector_payload_binding_v2 import ConstructionObligationProjectorRunnerPayloadV2, DurableConstructionObligationProjectorPayloadBinderV2


def _prepared(root):
    return StagePConstructionObligationProjectorEvaluatorInterfaceV1(
        project_root=root).prepare({"factual_summary":"Autoritatea a publicat rezultatul.",
                                    "candidate":"Dosarul si-a pus cravata pentru fotografie."})


def test_host_payload_and_runner_projector_bind_without_execution(project_root):
    prepared = _prepared(project_root)
    raw = DurableConstructionObligationProjectorPayloadBinderV2(
        project_root=project_root).build(prepared)
    payload = ConstructionObligationProjectorRunnerPayloadV2(raw_payload=raw)
    projector = payload.bind_projector(token_pieces={0:"{"}, eos_token_id=1,
                                               excluded_token_ids=())
    assert payload.prompt == prepared.rendered_prompt
    assert payload.max_new_tokens == 3200
    assert projector.allowed_token_ids([], lambda ids: "") == (0,)


def test_payload_is_canonical_and_tamper_fails_closed(project_root):
    prepared = _prepared(project_root); binder = DurableConstructionObligationProjectorPayloadBinderV2(project_root=project_root)
    assert binder.build(prepared) == binder.build(prepared)
    value = json.loads(binder.build(prepared))
    mutations = []
    changed = dict(value); changed["projector_identity"] = "0" * 64; mutations.append(changed)
    changed = dict(value); changed["extra"] = True; mutations.append(changed)
    for mutation in mutations:
        with pytest.raises(ValueError):
            ConstructionObligationProjectorRunnerPayloadV2(
                raw_payload=(json.dumps(mutation,separators=(",",":")) + "\n").encode())


@pytest.fixture
def project_root():
    from pathlib import Path
    return Path(__file__).resolve().parents[1]
