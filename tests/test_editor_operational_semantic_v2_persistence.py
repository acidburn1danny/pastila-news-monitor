from __future__ import annotations

import hashlib
import json

import pytest
from test_editor_application_serialization_v1 import completed_result
from test_editor_operational_execution_v1 import (
    execute_fake,
    observation,
    trace_node,
)

from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import (
    GenerationComponentType,
    GenerationTrace,
)
from pastila_scout.editor.generation.semantic_draft_v2 import (
    AuthorityDensityV2,
    ControlledSemanticGenerationResultV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticGenerationStateV2,
    SemanticStoryV2,
)
from pastila_scout.editor_application_v1 import (
    EditorApplicationSerializationError,
    EditorOperationalResultSerializerV1,
    load_editor_operational_result_v1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalGenerationStatusV1,
)
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2


def _semantic_output() -> ControlledSemanticGenerationResultV2:
    summary = FactualSummaryV2(
        text="Autoritatea locală a confirmat măsura.",
        authority_bundle_identity="sha256:authority",
        authority_density=AuthorityDensityV2.STANDARD,
        nucleus_bindings=(
            FactualNucleusBindingV2(
                nucleus_id="measure",
                sentence_number=1,
                authority_fact_ids=("authority:fact-1",),
            ),
        ),
        model_identifier="pastila-editor-core-v1.2-experimental",
        provider="openai",
        validation_receipt="sha256:validation",
    )
    draft = PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-v2",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(
            SemanticStoryV2(
                event_id=2566,
                position=1,
                factual_summary=summary,
                acid_commentary=None,
                acid_commentary_status="absent_voice_layer_unavailable",
            ),
        ),
        provenance_references=("sha256:authority",),
        generation_receipts=("sha256:validation",),
    )
    return ControlledSemanticGenerationResultV2(
        draft=draft,
        trace=GenerationTrace(
            attempts=(
                trace_node("a", GenerationComponentType.STORY, "openai"),
            )
        ),
        manifest=GenerationManifest.build_semantic_v2(
            (2566,), include_transitions=False, maximum_attempts=3
        ),
        final_state=SemanticGenerationStateV2(
            revision=1, accepted_event_ids=(2566,)
        ),
    )


def _v2_operational(monkeypatch: pytest.MonkeyPatch):
    result, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.COMPLETED),),
        output=_semantic_output(),
    )
    assert result.status is EditorOperationalGenerationStatusV1.COMPLETED
    assert type(result.draft) is PastilaEditorSemanticDraftV2
    return result


def _rewrite_payload(serialized, mutate):
    envelope = json.loads(serialized.payload)
    mutate(envelope)
    envelope["payload_sha256"] = ""
    blank = (
        json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    checksum = f"sha256:{hashlib.sha256(blank).hexdigest()}"
    envelope["payload_sha256"] = checksum
    payload = (
        json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    return payload, checksum


def test_v1_persistence_shape_and_round_trip_remain_identical(monkeypatch, tmp_path):
    result = completed_result(monkeypatch)
    serializer = EditorOperationalResultSerializerV1()
    serialized = serializer.serialize(result=result)
    projection = json.loads(serialized.payload)["operational_result"]["draft"]
    assert "schema_name" not in projection and "schema_version" not in projection
    path = tmp_path / "v1.json"
    path.write_bytes(serialized.payload)
    loaded = load_editor_operational_result_v1(
        path=path, payload_sha256=serialized.payload_sha256
    )
    assert serializer.serialize(result=loaded) == serialized


def test_v2_operational_completion_persists_native_and_round_trips(monkeypatch, tmp_path):
    result = _v2_operational(monkeypatch)
    serializer = EditorOperationalResultSerializerV1()
    serialized = serializer.serialize(result=result)
    envelope = json.loads(serialized.payload)
    projection = envelope["operational_result"]["draft"]
    assert projection["schema_name"] == "pastila-editor-semantic-draft"
    assert projection["schema_version"] == "2"
    assert projection["stories"][0]["factual_summary"]["text"] == (
        "Autoritatea locală a confirmat măsura."
    )
    assert projection["provenance_references"] == ["sha256:authority"]
    assert projection["generation_receipts"] == ["sha256:validation"]
    assert projection["assembled_text"] == projection["teleprompter_text"]

    path = tmp_path / "v2.json"
    path.write_bytes(serialized.payload)
    loaded = load_editor_operational_result_v1(
        path=path, payload_sha256=serialized.payload_sha256
    )
    assert type(loaded.draft) is PastilaEditorSemanticDraftV2
    assert loaded.draft == result.draft
    assert loaded.result_fingerprint == result.result_fingerprint
    assert serializer.serialize(result=loaded) == serialized


@pytest.mark.parametrize("corruption", ["version", "assembly"])
def test_v2_unknown_version_and_invalid_assembly_fail_closed(
    monkeypatch, tmp_path, corruption
):
    serialized = EditorOperationalResultSerializerV1().serialize(
        result=_v2_operational(monkeypatch)
    )

    def mutate(envelope):
        draft = envelope["operational_result"]["draft"]
        if corruption == "version":
            draft["schema_version"] = "999"
        else:
            draft["assembled_text"] = "text care nu corespunde componentelor"

    payload, checksum = _rewrite_payload(serialized, mutate)
    path = tmp_path / f"invalid-{corruption}.json"
    path.write_bytes(payload)
    with pytest.raises(EditorApplicationSerializationError):
        load_editor_operational_result_v1(path=path, payload_sha256=checksum)
