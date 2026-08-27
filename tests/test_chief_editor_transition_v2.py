from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from test_active_project_v1 import _additional_event, _database
from test_chief_editor_v2_handoff import _persist

from pastila_scout.active_project_v1 import ActiveProjectStoreV1, ChiefEditorItemV1
from pastila_scout.chief_editor_transition_v2 import (
    AcceptedTransitionV1,
    ChiefEditorTransitionWorkflowStoreV1,
    PublicTransitionStateV1,
    TransitionAdjacencySlotV1,
    TransitionAttemptV1,
    TransitionValidationResultV1,
    build_transition_adjacency_slot,
    chief_story_reference_identity,
    reconcile_transition_workflow,
    transition_sidecar_path,
)
from pastila_scout.chief_editor_v2_handoff import (
    create_chief_editor_v2_story_reference,
)
from pastila_scout.desktop_v1.entrypoint import _publish_chief_editor
from pastila_scout.voice_workflow_v2 import sha256_identity

NOW = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)


def _reference(monkeypatch, tmp_path, event_id, suffix, *, summary=None):
    path = tmp_path / f"{suffix}.json"
    _, payload_sha256 = _persist(
        monkeypatch,
        path,
        event_id=event_id,
        summary_text=summary,
    )
    reference = create_chief_editor_v2_story_reference(
        material_reference=f"editor-material-v1:event:{event_id}",
        event_id=event_id,
        output_path=path,
        payload_sha256=payload_sha256,
    )
    assert reference is not None
    return reference


def _entries(*references):
    return tuple(
        (reference, reference.material_reference, "") for reference in references
    )


def _generated(slot, text="De la primul subiect trecem la al doilea."):
    attempt = TransitionAttemptV1(
        attempt_identity=sha256_identity("transition-attempt"),
        ordinal=1,
        outcome="generated",
        transition_input_identity=slot.transition_input_identity,
        model_package_identity="transition-package:v1",
        output_sha256=sha256_identity(text),
        validation_result=TransitionValidationResultV1.PASSED,
        validation_receipt="transition-boundary:pass",
        started_at=NOW,
        completed_at=NOW,
    )
    accepted = AcceptedTransitionV1(
        text=text,
        output_sha256=sha256_identity(text),
        attempt_identity=attempt.attempt_identity,
        model_package_identity="transition-package:v1",
        validation_receipt="transition-boundary:pass",
    )
    payload = slot.model_dump(mode="python")
    payload.update(
        {
            "state": PublicTransitionStateV1.GENERATED,
            "attempts": (attempt,),
            "accepted_transition": accepted,
        }
    )
    return TransitionAdjacencySlotV1.model_validate(payload)


def test_typed_directed_adjacency_identity_and_generated_text_are_exact(
    monkeypatch, tmp_path
):
    a = _reference(monkeypatch, tmp_path, 101, "a")
    b = _reference(monkeypatch, tmp_path, 102, "b")
    forward = build_transition_adjacency_slot(from_reference=a, to_reference=b)
    reverse = build_transition_adjacency_slot(from_reference=b, to_reference=a)
    assert forward.adjacency_identity != reverse.adjacency_identity
    assert forward.from_story.story_revision_identity == a.story_revision_identity
    assert forward.to_story.story_revision_identity == b.story_revision_identity
    assert forward.state is PublicTransitionStateV1.UNAVAILABLE
    generated = _generated(forward, "Text de tranziție byte-exact.")
    assert generated.accepted_transition is not None
    assert generated.accepted_transition.text == "Text de tranziție byte-exact."


def test_transition_sidecar_round_trip_is_deterministic(monkeypatch, tmp_path):
    a = _reference(monkeypatch, tmp_path, 101, "a")
    b = _reference(monkeypatch, tmp_path, 102, "b")
    sidecar = reconcile_transition_workflow(
        references_and_intents=_entries(a, b), existing=None, now=NOW
    )
    generated = _generated(sidecar.active_slots[0], "Text persistat exact.")
    sidecar = sidecar.model_copy(update={"active_slots": (generated,)})
    path = tmp_path / "transitions.json"
    store = ChiefEditorTransitionWorkflowStoreV1(path)
    first_identity = store.save(sidecar)
    reloaded = store.load()
    assert reloaded == sidecar
    assert reloaded.active_slots[0].accepted_transition is not None
    assert reloaded.active_slots[0].accepted_transition.text == "Text persistat exact."
    assert store.save(reloaded) == first_identity


def test_insert_swap_remove_and_endpoint_replacement_retire_old_slot(
    monkeypatch, tmp_path
):
    a = _reference(monkeypatch, tmp_path, 101, "a")
    b = _reference(monkeypatch, tmp_path, 102, "b")
    c = _reference(monkeypatch, tmp_path, 103, "c")
    initial = reconcile_transition_workflow(
        references_and_intents=_entries(a, b), existing=None, now=NOW
    )
    ab = initial.active_slots[0]

    inserted = reconcile_transition_workflow(
        references_and_intents=_entries(a, c, b), existing=initial, now=NOW
    )
    assert ab.adjacency_identity not in {
        item.adjacency_identity for item in inserted.active_slots
    }
    assert ab in inserted.retired_slots

    swapped = reconcile_transition_workflow(
        references_and_intents=_entries(b, a), existing=initial, now=NOW
    )
    assert ab in swapped.retired_slots

    removed = reconcile_transition_workflow(
        references_and_intents=_entries(a), existing=initial, now=NOW
    )
    assert removed.active_slots == () and ab in removed.retired_slots

    newer_a = _reference(
        monkeypatch,
        tmp_path,
        101,
        "newer-a",
        summary="Autoritatea a confirmat o versiune factuală nouă.",
    )
    replaced = reconcile_transition_workflow(
        references_and_intents=_entries(newer_a, b), existing=initial, now=NOW
    )
    assert ab in replaced.retired_slots


def test_unrelated_reorder_preserves_exact_pair_local_transition(monkeypatch, tmp_path):
    a = _reference(monkeypatch, tmp_path, 101, "a")
    b = _reference(monkeypatch, tmp_path, 102, "b")
    c = _reference(monkeypatch, tmp_path, 103, "c")
    initial = reconcile_transition_workflow(
        references_and_intents=_entries(a, b, c), existing=None, now=NOW
    )
    generated_ab = _generated(initial.active_slots[0])
    initial = initial.model_copy(
        update={"active_slots": (generated_ab, initial.active_slots[1])}
    )
    reordered = reconcile_transition_workflow(
        references_and_intents=_entries(c, a, b), existing=initial, now=NOW
    )
    ab = next(
        item
        for item in reordered.active_slots
        if item.from_story.chief_story_reference_identity
        == chief_story_reference_identity(a)
    )
    assert ab == generated_ab
    assert ab.accepted_transition is not None


def test_historical_story_between_v2_endpoints_prevents_orphan_slot(
    monkeypatch, tmp_path
):
    a = _reference(monkeypatch, tmp_path, 101, "a")
    b = _reference(monkeypatch, tmp_path, 102, "b")
    sidecar = reconcile_transition_workflow(
        references_and_intents=(
            (a, a.material_reference, ""),
            (None, "editor-material-v1:event:999", ""),
            (b, b.material_reference, ""),
        ),
        existing=None,
        now=NOW,
    )
    assert sidecar.active_slots == ()


def test_active_project_order_persists_and_invalidates_transition_slots(
    monkeypatch, tmp_path
):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    _additional_event(database, 101, "A")
    _additional_event(database, 102, "B")
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    store.handoff_many(event_ids=(101, 102))
    for event_id in (101, 102):
        path = tmp_path / f"material-{event_id}.json"
        _, payload_sha256 = _persist(monkeypatch, path, event_id=event_id)
        store.mark_editor_item_running(event_id=event_id)
        store.record_editor_output_for_event(
            event_id=event_id,
            output_path=path,
            payload_sha256=payload_sha256,
        )
    transition_store = ChiefEditorTransitionWorkflowStoreV1(
        transition_sidecar_path(project_path)
    )
    first = transition_store.load()
    assert len(first.active_slots) == 1
    project = store.load()
    assert project is not None
    stale_project = replace(
        project, chief_editor_items=tuple(reversed(project.chief_editor_items))
    )
    published = {}

    class View:
        def publish_chief_editor(self, **kwargs):
            published.update(kwargs)

    _publish_chief_editor(View(), stale_project, store=store)
    assert "nu mai corespunde" in published["status"]
    assert all(
        "Tranziție către" not in text
        for _reference, text in published["v2_presentations"]
    )
    reversed_items = tuple(
        ChiefEditorItemV1(
            material_reference=item.material_reference,
            section=item.section,
            note=item.note,
        )
        for item in reversed(project.chief_editor_items)
    )
    store.save_chief_editor(title="Ordine nouă", items=reversed_items)
    restarted = ChiefEditorTransitionWorkflowStoreV1(
        transition_sidecar_path(project_path)
    ).load()
    assert len(restarted.active_slots) == 1
    assert first.active_slots[0] in restarted.retired_slots
    assert (
        restarted.active_slots[0].adjacency_identity
        != first.active_slots[0].adjacency_identity
    )
