from test_active_project_v1 import _additional_event, _database

from pastila_scout.active_project_v1 import ActiveProjectStoreV1


def test_latest_handoff_view_persists_without_deleting_worklist_history(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    _additional_event(database, 8, "Al doilea material")
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    project, _ = store.handoff_many(event_ids=(7, 8))

    projected = store.record_latest_handoff_view(event_ids=(8,))

    assert projected.editor_worklist == project.editor_worklist
    assert projected.scout_input == project.scout_input
    assert projected.latest_handoff_event_ids == (8,)
    assert store.load_runtime_state() == projected
