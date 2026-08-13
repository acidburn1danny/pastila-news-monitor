from pathlib import Path
from types import SimpleNamespace

import pytest

from pastila_scout.desktop_v1.editor_batch import (
    _EditorBatchResultV1,
    _run_editor_batch_v1,
)


class _Store:
    def __init__(self, event_ids):
        self.status = {event_id: "pending" for event_id in event_ids}
        self.materials = []

    def load_runtime_state(self):
        return SimpleNamespace(
            editor_worklist=tuple(
                SimpleNamespace(event_id=event_id, status=SimpleNamespace(value=status))
                for event_id, status in self.status.items()
            )
        )

    def mark_editor_item_running(self, *, event_id):
        assert self.status[event_id] == "pending"
        self.status[event_id] = "running"

    def record_editor_output_for_event(self, *, event_id, output_path, payload_sha256):
        assert self.status[event_id] == "running"
        self.materials.append((event_id, output_path, payload_sha256))

    def mark_editor_item_completed(self, *, event_id):
        assert self.status[event_id] == "running"
        self.status[event_id] = "completed"

    def mark_editor_item_failed(self, *, event_id):
        assert self.status[event_id] == "running"
        self.status[event_id] = "failed"


def test_batch_executes_each_selected_event_once_in_authoritative_order(tmp_path):
    store = _Store((2, 4, 5))
    calls = []

    def execute(event_id):
        calls.append(event_id)
        return tmp_path / f"editor-{event_id}.json", f"sha256:{event_id:064x}"

    result = _run_editor_batch_v1(store=store, event_ids=(5, 2, 4), execute=execute)

    assert calls == [2, 4, 5]
    assert result.attempted_event_ids == (2, 4, 5)
    assert result.completed_event_ids == (2, 4, 5)
    assert result.failed_event_ids == ()
    assert store.status == {2: "completed", 4: "completed", 5: "completed"}
    assert tuple(item[0] for item in store.materials) == (2, 4, 5)


@pytest.mark.parametrize("failed_event_id", [2, 4, 5])
def test_batch_preserves_success_and_continues_after_item_failure(
    tmp_path, failed_event_id
):
    store = _Store((2, 4, 5))
    calls = []

    def execute(event_id):
        calls.append(event_id)
        if event_id == failed_event_id:
            raise RuntimeError("bounded item failure")
        return Path(tmp_path / f"editor-{event_id}.json"), f"sha256:{event_id:064x}"

    result = _run_editor_batch_v1(store=store, event_ids=(2, 4, 5), execute=execute)

    expected_completed = tuple(value for value in (2, 4, 5) if value != failed_event_id)
    assert calls == [2, 4, 5]
    assert result.completed_event_ids == expected_completed
    assert result.failed_event_ids == (failed_event_id,)
    assert store.status[failed_event_id] == "failed"
    assert all(store.status[value] == "completed" for value in expected_completed)


def test_batch_does_not_swallow_coordinator_level_interrupt():
    store = _Store((2, 4))

    def execute(event_id):
        del event_id
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _run_editor_batch_v1(store=store, event_ids=(2, 4), execute=execute)
    assert store.status == {2: "running", 4: "pending"}


def test_batch_rejects_unknown_or_mixed_state_before_execution():
    store = _Store((2, 4, 5))
    store.status[4] = "completed"
    calls = []
    for selection in ((2, 4), (2, 99)):
        with pytest.raises(ValueError):
            _run_editor_batch_v1(
                store=store,
                event_ids=selection,
                execute=lambda event_id: calls.append(event_id),
            )
    assert calls == []
    assert store.status == {2: "pending", 4: "completed", 5: "pending"}


@pytest.mark.parametrize(
    "values",
    (
        ((), (), ()),
        ((2, 2), (2,), ()),
        ((2, 4), (2,), ()),
        ((2,), (2,), (2,)),
        ((2, 4), (4, 2), ()),
    ),
)
def test_batch_result_rejects_impossible_identity_claims(values):
    with pytest.raises(ValueError):
        _EditorBatchResultV1(*values)
