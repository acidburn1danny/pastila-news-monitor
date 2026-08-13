from pathlib import Path
from types import SimpleNamespace

import httpx

from pastila_scout.contracts.samples import sample_scout_input
from pastila_scout.desktop_v1.first_run import _complete_desktop_setup_v1
from pastila_scout.desktop_v1.integrated_editor import _integrated_editor_request_v1
from pastila_scout.editor.engine import SelectionEngine
from pastila_scout.editor_application_v1.configuration import (
    EditorApplicationGenerationConfigurationAuthorityV1,
)
from pastila_scout.editor_generation_runtime_v1.composition import (
    _create_editor_generation_runtime_session_factory_v1,
    _EditorAttemptReferenceFactoryV1,
)
from pastila_scout.editor_operational_v1 import EditorOperationalCoordinatorV1
from pastila_scout.provider_execution_ollama_v1 import OllamaHttpClientV1
from pastila_scout.windows_state_v1.settings import _default_windows_settings_v1

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "src/pastila_scout/desktop_v1/default-settings-v1.json"


def test_recovered_project_builds_complete_ollama_editor_request(tmp_path):
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    settings = _complete_desktop_setup_v1(
        settings=settings,
        settings_path=tmp_path / "settings.json",
        provider="ollama",
        base_url="http://localhost:11434",
        model="qwen3:14b",
        output_directory=tmp_path / "reports",
    )
    source = sample_scout_input()
    project = SimpleNamespace(scout_input=source, candidate=source.ranked_events[0])
    request = _integrated_editor_request_v1(project=project, settings=settings)
    assert request.scout_input == source
    assert request.generation_configuration.provider.value == "ollama"
    assert request.generation_configuration.model_identifier == "qwen3:14b"
    assert request.generation_configuration.max_output_tokens == 2000
    assert request.episode_context.mandatory_event_ids == (project.candidate.event_id,)
    assert request.selection_profile.minimum_source_diversity == (
        project.candidate.source_count
    )
    assert request.destination.path.parent == settings.editor_output_directory
    preparation = EditorOperationalCoordinatorV1(SelectionEngine()).prepare(
        scout_input=request.scout_input,
        selection_profile=request.selection_profile,
        episode_context=request.episode_context,
    )
    assert preparation.plan is not None
    materialized = EditorApplicationGenerationConfigurationAuthorityV1()._materialize(
        configuration=request.generation_configuration
    )
    session = _create_editor_generation_runtime_session_factory_v1().open(
        materialized.runtime_options,
        operation_reference=request.operation_reference,
    )
    assert session.operation_reference == request.operation_reference
    session.close()


def test_ollama_model_discovery_uses_tags_and_exact_names():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "qwen3:14b"}, {"name": "gemma3:4b"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert OllamaHttpClientV1(client).list_models(
            base_url="http://localhost:11434", timeout=3.0
        ) == ("qwen3:14b", "gemma3:4b")


def test_production_attempt_reference_accepts_canonical_prompt_fingerprint():
    factory = _EditorAttemptReferenceFactoryV1(operation_reference="editor-operation-1")
    prefixed = factory.create(prompt_fingerprint="sha256:" + "a" * 64, attempt_number=1)
    legacy = factory.create(prompt_fingerprint="a" * 64, attempt_number=1)
    assert prefixed == legacy
