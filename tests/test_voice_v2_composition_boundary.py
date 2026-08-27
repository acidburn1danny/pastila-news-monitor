from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production


def test_voice_composition_without_project_or_settings_binds_no_runtime_provider():
    composition = compose_voice_v2_production()

    assert composition.canonical_store is None
    assert composition.persisted_context_loader is None
    assert composition.adjudication_store is None
    assert composition.ordinary_story_bootstrap is None
    assert composition.desktop_adjudication is None
