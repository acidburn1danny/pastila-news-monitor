"""Offline verification of the opt-in real Scout caller migration."""

from __future__ import annotations

import copy
import json
import pickle
import subprocess
import sys
from datetime import UTC, datetime
from functools import partial, wraps
from inspect import Signature
from pathlib import Path

import pytest

from pastila_scout.ai.openai_provider import OpenAIProvider
from pastila_scout.ai.provider import ProviderError, StructuredAIResponse
from pastila_scout.ai.verification import EventVerifier
from pastila_scout.cli import build_parser
from pastila_scout.config import AIConfig
from pastila_scout.models.ai import EventVerificationRequest, VerificationArticle
from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
)
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeResultV1
from pastila_scout.verify_event_candidates_runtime_v1 import (
    ProviderNeutralEventVerificationProviderV1,
    build_event_verification_task,
    composition,
    serialize_event_verification_task,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 5, 10, tzinfo=UTC)


def _article(article_id: int) -> VerificationArticle:
    return VerificationArticle(
        article_id=article_id,
        event_id=article_id,
        normalized_title=f"Exact title {article_id}",
        summary=f"Exact summary {article_id}",
        published_at="2026-08-05T09:00:00+00:00",
        source_id=f"source-{article_id}",
        source_name=f"Source {article_id}",
        url=f"https://example.com/{article_id}",
        categories=("Social",),
    )


def _request() -> EventVerificationRequest:
    return EventVerificationRequest(
        left=_article(1), right=_article(2), deterministic_similarity=0.91
    )


def _decision() -> str:
    return json.dumps(
        {
            "same_event": True,
            "ai_similarity_score": 92,
            "same_people": None,
            "same_institution": True,
            "same_location": None,
            "same_context": True,
            "reasoning": "Exact downstream decision.",
        }
    )


class _FakeExecution:
    def __init__(self, generated_text: str = "") -> None:
        self.generated_text = generated_text or _decision()
        self.calls: list[tuple[ProviderChoiceV1, ProviderExecutionRequestV2]] = []

    def __call__(
        self, provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
    ) -> ScoutRuntimeResultV1:
        self.calls.append((provider, request))
        source = request.request_envelope.request_units[0].source_request_reference
        return ScoutRuntimeResultV1(
            ProviderExecutionResultV2(
                request_id=request.context.request_id,
                provider_id=request.provider.provider_id,
                request_envelope_identity=request.request_envelope.identity,
                outcome=ExecutionOutcomeV2.COMPLETED,
                finished_at=NOW,
                provider_result=ProviderResultProjectionV2(
                    status=ProviderResultStatusV2.SUCCESS,
                    outputs=(
                        ProviderOutputInputV2(
                            source_request_reference=source,
                            ordinal=0,
                            generated_text=self.generated_text,
                            finish_reason=ProviderFinishReasonV2.COMPLETED,
                        ),
                    ),
                ),
            )
        )


def _runner(fake: _FakeExecution):
    def execute(
        provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
    ) -> ScoutRuntimeResultV1:
        return fake(provider, request)

    return execute


def _unused_execute(
    provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
) -> ScoutRuntimeResultV1:
    del provider, request
    raise AssertionError("dependency body was invoked during validation")


def test_structured_task_is_identical_to_existing_openai_prompt_construction() -> None:
    captured = []

    class Capture:
        def complete_structured(self, task):
            captured.append(task)
            return StructuredAIResponse(_decision())

    OpenAIProvider.verify_with_diagnostics(Capture(), _request())

    assert captured == [build_event_verification_task(_request())]


@pytest.mark.parametrize("choice", tuple(ProviderChoiceV1))
def test_provider_neutral_execution_preserves_prompt_and_output_once(choice) -> None:
    fake = _FakeExecution()
    provider = ProviderNeutralEventVerificationProviderV1(
        choice, _runner(fake), now=lambda: NOW
    )

    output = provider.verify(_request())

    assert output == _decision()
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is choice
    prompt = fake.calls[0][1].request_intent.request_units[0].messages[0].content
    assert prompt == serialize_event_verification_task(
        build_event_verification_task(_request())
    )


@pytest.mark.parametrize("choice", tuple(ProviderChoiceV1))
def test_existing_verifier_parsing_and_decision_are_unchanged(tmp_path, choice) -> None:
    fake = _FakeExecution()
    provider = ProviderNeutralEventVerificationProviderV1(
        choice, _runner(fake), now=lambda: NOW
    )
    verifier = EventVerifier(
        AIConfig(enable_ai=True, retry_delay=0.0),
        type(
            "EmptyCache",
            (),
            {
                "get": lambda self, key: type(
                    "Lookup", (), {"result": None, "status": "miss"}
                )(),
                "put": lambda self, key, result: None,
            },
        )(),
        provider,
        api_key_available=True,
        now=lambda: NOW,
    )

    result = verifier.verify(_request())

    assert result.status == "success"
    assert result.same_event is True
    assert result.ai_similarity_score == 92
    assert result.reasoning == "Exact downstream decision."
    assert verifier.ai_requests == len(fake.calls) == 1
    assert result.retry_count == 0


def test_provider_failure_is_non_retryable() -> None:
    def fail(
        provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
    ) -> ScoutRuntimeResultV1:
        del provider, request
        raise RuntimeError("private provider detail")

    provider = ProviderNeutralEventVerificationProviderV1(
        ProviderChoiceV1.OPENAI, fail, now=lambda: NOW
    )

    with pytest.raises(ProviderError) as captured:
        provider.verify(_request())
    assert captured.value.retryable is False
    assert str(captured.value) == "Provider-neutral event verification failed"
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_adapter_validation_does_not_invoke_dependency_body() -> None:
    adapter = ProviderNeutralEventVerificationProviderV1(
        ProviderChoiceV1.OPENAI, _unused_execute, now=lambda: NOW
    )
    assert "0x" not in repr(adapter)


@pytest.mark.parametrize(
    ("provider", "execute"),
    (
        ("openai", _unused_execute),
        (ProviderChoiceV1.OPENAI, object()),
        (ProviderChoiceV1.OPENAI, partial(_unused_execute)),
        (ProviderChoiceV1.OPENAI, staticmethod(_unused_execute)),
        (ProviderChoiceV1.OPENAI, classmethod(_unused_execute)),
    ),
)
def test_adapter_rejects_invalid_provider_and_callable_dependencies(
    provider, execute
) -> None:
    with pytest.raises(
        ValueError, match="^invalid provider-neutral verification dependency$"
    ):
        ProviderNeutralEventVerificationProviderV1(provider, execute, now=lambda: NOW)


def test_adapter_rejects_wrapped_forged_and_wrongly_annotated_functions() -> None:
    @wraps(_unused_execute)
    def wrapped(*args, **kwargs):
        return _unused_execute(*args, **kwargs)

    def forged(
        provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
    ) -> ScoutRuntimeResultV1:
        return _unused_execute(provider, request)

    forged.__signature__ = Signature()

    def wrong_return(
        provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
    ) -> object:
        return _unused_execute(provider, request)

    for execute in (wrapped, forged, wrong_return):
        with pytest.raises(ValueError):
            ProviderNeutralEventVerificationProviderV1(
                ProviderChoiceV1.OPENAI, execute, now=lambda: NOW
            )


def test_adapter_copy_pickle_dynamic_attribute_and_corruption_policies() -> None:
    adapter = ProviderNeutralEventVerificationProviderV1(
        ProviderChoiceV1.OPENAI, _unused_execute, now=lambda: NOW
    )

    assert copy.copy(adapter) is adapter
    assert copy.deepcopy(adapter) is adapter
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(adapter)
    with pytest.raises(AttributeError):
        adapter.dynamic_dependency = object()

    object.__setattr__(adapter, "_provider", "openai")
    with pytest.raises(
        ValueError, match="invalid provider-neutral verification adapter"
    ):
        copy.copy(adapter)


@pytest.mark.parametrize(
    ("choice", "selected_name", "unselected_name"),
    (
        (ProviderChoiceV1.OPENAI, "_run_openai", "_run_ollama"),
        (ProviderChoiceV1.OLLAMA, "_run_ollama", "_run_openai"),
    ),
)
def test_command_composition_calls_only_selected_verified_path_once(
    monkeypatch, choice, selected_name, unselected_name
) -> None:
    from pastila_scout.scout_cli_provider_run_v1 import composition as cli_composition

    calls = []
    expected = object()

    def selected(provider, request):
        calls.append((provider, request))
        return expected

    def unselected(provider, request):
        del provider, request
        raise AssertionError("unselected provider executed")

    monkeypatch.setattr(cli_composition, selected_name, selected)
    monkeypatch.setattr(cli_composition, unselected_name, unselected)
    request = object()

    result = composition._execute_provider_request(choice, request)

    assert result is expected
    assert calls == [(choice, request)]


def test_cli_provider_vocabulary_is_exact_and_legacy_path_remains_available() -> None:
    parser = build_parser()
    assert parser.parse_args(["verify-event-candidates"]).provider is None
    for provider in ("openai", "ollama"):
        assert (
            parser.parse_args(
                ["verify-event-candidates", "--provider", provider]
            ).provider
            == provider
        )
    for invalid in ("OPENAI", "auto", "default", "local", "remote"):
        with pytest.raises(SystemExit) as captured:
            parser.parse_args(["verify-event-candidates", "--provider", invalid])
        assert captured.value.code == 2


def test_help_is_passive_and_does_not_load_runtime_package() -> None:
    script = """
import sys
from pastila_scout.cli import main
try:
    main(['verify-event-candidates', '--help'])
except SystemExit as error:
    assert error.code == 0
assert 'pastila_scout.verify_event_candidates_runtime_v1' not in sys.modules
assert 'pastila_scout.scout_cli_provider_run_v1.composition' not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-W", "error", "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "--provider {openai,ollama}" in completed.stdout
