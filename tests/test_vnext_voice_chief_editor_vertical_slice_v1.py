from __future__ import annotations

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_product_orchestrator_v1 import PolicyInstruction, ProductOrchestrator, bootstrap_store
from pastila_scout.vnext_voice_chief_editor_v1 import VoiceBoundaryError, build_voice_draft
from test_vnext_product_orchestrator_integrated_core_e2e_v1 import factual_instruction, prepare


class VoiceBackend:
    backend_identity = object_identity({"backend": "test-injected"})
    model_identity = object_identity({"model": "candidate-not-promoted"})
    decoding_identity = object_identity({"temperature": 0, "top_p": 1})

    def realize(self, request):
        return {
            "request_identity": request["request_identity"],
            "status": "COMMENTARY",
            "commentary": "Miza editoriala este impactul masurii asupra bugetului public.",
        }


def policy_instruction(outcome="APPROVE_FINAL"):
    return PolicyInstruction(
        actor="chief-editor",
        outcome=outcome,
        authorization_identity=object_identity({"authority": "chief-editor", "outcome": outcome}),
        reason_code="CHIEF_EDITOR_REVIEWED",
    )


def factual_bundle(tmp_path):
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-10-02T08:03:00Z",
    )
    return store, orchestrator, factual


def test_voice_to_chief_editor_to_exported(tmp_path):
    store, orchestrator, factual = factual_bundle(tmp_path)
    voice = orchestrator.apply_voice(
        factual,
        instruction="Add bounded commentary without changing facts.",
        seed=17,
        backend=VoiceBackend(),
        observed_at="2026-10-02T08:04:00Z",
    )
    exported = orchestrator.apply_chief_editor_and_export(
        voice,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-10-02T08:05:00Z",
        policy_decision_observed_at="2026-10-02T08:06:00Z",
        final_observed_at="2026-10-02T08:07:00Z",
    )
    assert store.load_workflow(factual.workflow_identity)["state"] == "EXPORTED"
    assert exported.final["voice_mode"] == "ENABLED"
    assert exported.final["factual_setup"] == factual.artifact["text"]
    assert exported.final["commentary"] == voice.draft["commentary"]
    assert exported.final["voice_draft_identity"] == voice.draft["artifact_identity"]
    assert store.verify_integrity() == {"status": "PASS", "schema_version": 8, "foreign_key_violations": 0}


def test_restart_rehydrates_voice_and_completes_chief_editor(tmp_path):
    _, orchestrator, factual = factual_bundle(tmp_path)
    voice = orchestrator.apply_voice(
        factual,
        instruction="Commentary only.",
        seed=23,
        backend=VoiceBackend(),
        observed_at="2026-10-02T08:04:00Z",
    )
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_voice_draft_bundle(factual.workflow_identity)
    assert loaded == voice
    result = restarted.apply_chief_editor_and_export(
        loaded,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-10-02T08:05:00Z",
        policy_decision_observed_at="2026-10-02T08:06:00Z",
        final_observed_at="2026-10-02T08:07:00Z",
    )
    assert result.final["assembly"] == "DETERMINISTIC_SETUP_COMMENTARY_V1"


def test_voice_fails_closed_on_factual_mutation_and_unbound_response(tmp_path):
    _, _, factual = factual_bundle(tmp_path)
    changed = dict(factual.artifact)
    changed["text"] = "altered"
    with pytest.raises(VoiceBoundaryError, match="artifact_identity mismatch"):
        build_voice_draft(workflow_identity=factual.workflow_identity, factual=changed, instruction="x", seed=1, backend=VoiceBackend())

    class Unbound(VoiceBackend):
        def realize(self, request):
            return {"request_identity": "0" * 64, "status": "COMMENTARY", "commentary": "x"}

    with pytest.raises(VoiceBoundaryError, match="not bound"):
        build_voice_draft(workflow_identity=factual.workflow_identity, factual=factual.artifact, instruction="x", seed=1, backend=Unbound())


def test_seed_stability_and_repetition_identity(tmp_path):
    _, _, factual = factual_bundle(tmp_path)
    first = build_voice_draft(workflow_identity=factual.workflow_identity, factual=factual.artifact, instruction="same", seed=9, backend=VoiceBackend())
    second = build_voice_draft(workflow_identity=factual.workflow_identity, factual=factual.artifact, instruction="same", seed=9, backend=VoiceBackend())
    assert first == second
    assert first["repetition_identity"] == object_identity({"commentary": first["commentary"]})


def test_voice_remains_unpromoted_in_active_product_contract():
    # This isolated slice exposes no default backend and cannot activate itself.
    import inspect
    from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestrator
    signature = inspect.signature(ProductOrchestrator.apply_voice)
    assert signature.parameters["backend"].default is inspect.Parameter.empty
