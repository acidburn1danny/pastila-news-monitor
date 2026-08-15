"""Offline verification of provider-neutral rank-events execution."""

from __future__ import annotations

import copy
import json
import pickle
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_event_scoring import _decision, _event

from pastila_scout.ai.cache import FileJSONCache
from pastila_scout.ai.editorial_scoring import (
    EditorialEventScorer,
    build_editorial_scoring_task,
)
from pastila_scout.ai.provider import (
    ProviderError,
    StructuredAIRequest,
    StructuredAIResponse,
)
from pastila_scout.cli import build_parser
from pastila_scout.config import AIConfig, ScoringConfig
from pastila_scout.core.event_scoring import score_event_deterministically
from pastila_scout.models import EditorialScoringRequest
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
from pastila_scout.rank_events_runtime_v1 import (
    ProviderNeutralRankingProviderV1,
    composition,
    serialize_ranking_task,
)
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeResultV1

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 5, 10, tzinfo=UTC)


class _FakeExecution:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[tuple[ProviderChoiceV1, ProviderExecutionRequestV2]] = []

    def invoke(
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
                            generated_text=self.output,
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
        return fake.invoke(provider, request)

    return execute


def _task() -> StructuredAIRequest:
    scoring = ScoringConfig()
    event = _event()
    request = EditorialScoringRequest(
        event=event,
        deterministic_score=score_event_deterministically(
            event, scoring, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
        ),
    )
    return build_editorial_scoring_task(request, scoring)


@pytest.mark.parametrize("choice", tuple(ProviderChoiceV1))
def test_exact_structured_task_and_generated_text_are_preserved_once(choice) -> None:
    generated = " \n" + _decision() + "\n "
    fake = _FakeExecution(generated)
    provider = ProviderNeutralRankingProviderV1(choice, _runner(fake), now=lambda: NOW)

    response = provider.complete_structured(_task())

    assert response.output_text == generated
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is choice
    lower_prompt = fake.calls[0][1].request_intent.request_units[0].messages[0].content
    assert lower_prompt == serialize_ranking_task(_task())
    transported = json.loads(lower_prompt)
    task = _task()
    assert transported == {
        "name": task.name,
        "instructions": task.instructions,
        "input_json": task.input_json,
        "json_schema": task.json_schema,
    }


@pytest.mark.parametrize("choice", tuple(ProviderChoiceV1))
def test_existing_parser_score_and_cache_behavior_match_legacy(
    tmp_path, choice
) -> None:
    task_output = _decision()
    fake = _FakeExecution(task_output)
    neutral = ProviderNeutralRankingProviderV1(choice, _runner(fake), now=lambda: NOW)

    class Legacy:
        def complete_structured(self, task):
            del task
            return StructuredAIResponse(task_output)

    scoring = ScoringConfig()
    event = _event()
    request = EditorialScoringRequest(
        event=event,
        deterministic_score=score_event_deterministically(
            event, scoring, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
        ),
    )
    common = {
        "ai_config": AIConfig(enable_ai=True, retry_delay=0.0),
        "scoring_config": scoring,
        "api_key_available": True,
        "now": lambda: NOW,
    }
    legacy_result = EditorialEventScorer(
        cache=FileJSONCache(tmp_path / "legacy"), provider=Legacy(), **common
    ).score(request)
    neutral_result = EditorialEventScorer(
        cache=FileJSONCache(tmp_path / "neutral"), provider=neutral, **common
    ).score(request)

    assert neutral_result.decision == legacy_result.decision
    assert neutral_result.ai_editorial_score == legacy_result.ai_editorial_score
    assert neutral_result.status == legacy_result.status == "success"
    assert neutral_result.retry_count == legacy_result.retry_count == 0
    assert neutral_result.cache_status == legacy_result.cache_status == "miss"
    assert len(fake.calls) == 1


def test_malformed_json_reaches_existing_parser_without_repair(tmp_path) -> None:
    malformed = "```json\n{}\n```"
    fake = _FakeExecution(malformed)
    provider = ProviderNeutralRankingProviderV1(
        ProviderChoiceV1.OLLAMA, _runner(fake), now=lambda: NOW
    )
    scoring = ScoringConfig()
    event = _event()
    result = EditorialEventScorer(
        AIConfig(enable_ai=True, retry_delay=0.0),
        scoring,
        FileJSONCache(tmp_path / "cache"),
        provider,
        api_key_available=True,
        now=lambda: NOW,
    ).score(
        EditorialScoringRequest(
            event=event,
            deterministic_score=score_event_deterministically(
                event, scoring, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
            ),
        )
    )

    assert result.status == "invalid_response"
    assert fake.output == malformed
    assert len(fake.calls) == 1


@pytest.mark.parametrize(
    "outcome",
    (
        ExecutionOutcomeV2.PROVIDER_FAILURE,
        ExecutionOutcomeV2.TIMEOUT,
        ExecutionOutcomeV2.CANCELLED,
        ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
    ),
)
def test_neutral_failures_are_safe_nonretryable_and_execute_once(outcome) -> None:
    calls = []

    def execute(
        provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
    ) -> ScoutRuntimeResultV1:
        calls.append((provider, request))
        return ScoutRuntimeResultV1(
            ProviderExecutionResultV2(
                request_id=request.context.request_id,
                provider_id=request.provider.provider_id,
                request_envelope_identity=request.request_envelope.identity,
                outcome=outcome,
                finished_at=NOW,
                failure_code="safe-test-failure",
                failure_message="private lower detail",
            )
        )

    provider = ProviderNeutralRankingProviderV1(
        ProviderChoiceV1.OPENAI, execute, now=lambda: NOW
    )
    with pytest.raises(ProviderError) as captured:
        provider.complete_structured(_task())
    assert captured.value.retryable is False
    assert str(captured.value) == "Provider-neutral ranking failed"
    assert captured.value.__context__ is None
    assert len(calls) == 1


def test_adapter_object_safety_and_corruption_rejection() -> None:
    fake = _FakeExecution(_decision())
    adapter = ProviderNeutralRankingProviderV1(
        ProviderChoiceV1.OPENAI, _runner(fake), now=lambda: NOW
    )

    assert "0x" not in repr(adapter)
    assert copy.copy(adapter) is adapter
    assert copy.deepcopy(adapter) is adapter
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(adapter)
    with pytest.raises(AttributeError):
        adapter.dynamic_dependency = object()
    object.__setattr__(adapter, "_provider", "openai")
    with pytest.raises(ValueError, match="invalid provider-neutral ranking adapter"):
        copy.copy(adapter)


@pytest.mark.parametrize(
    ("choice", "selected_name", "unselected_name"),
    (
        (ProviderChoiceV1.OPENAI, "_run_openai", "_run_ollama"),
        (ProviderChoiceV1.OLLAMA, "_run_ollama", "_run_openai"),
    ),
)
def test_only_selected_verified_composition_executes(
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

    assert composition._execute_provider_request(choice, request) is expected
    assert calls == [(choice, request)]


def test_cli_provider_vocabulary_and_legacy_default_are_exact() -> None:
    parser = build_parser()
    assert parser.parse_args(["rank-events"]).provider is None
    for provider in ("openai", "ollama"):
        assert (
            parser.parse_args(["rank-events", "--provider", provider]).provider
            == provider
        )
    for invalid in ("OPENAI", "auto", "default", "local", "remote", " openai"):
        with pytest.raises(SystemExit) as captured:
            parser.parse_args(["rank-events", "--provider", invalid])
        assert captured.value.code == 2


def test_rank_help_is_passive() -> None:
    script = """
import sys
from pastila_scout.cli import main
try:
    main(['rank-events', '--help'])
except SystemExit as error:
    assert error.code == 0
assert 'pastila_scout.rank_events_runtime_v1' not in sys.modules
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
