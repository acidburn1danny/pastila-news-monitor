from __future__ import annotations

import copy
import inspect
import pickle
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.editor_generation_provider_adapter_v1 as api
from pastila_scout.editor.generation.models import (
    CallToActionGenerationResult,
    ClosingGenerationResult,
    CommentaryBlockResult,
    LanguageGenerationConfig,
    OpeningGenerationResult,
    StoryGenerationResult,
    TransitionGenerationResult,
)
from pastila_scout.editor.generation.prompt import (
    GenerationPrompt,
    PromptLayer,
    PromptSection,
)
from pastila_scout.editor.generation.provider import (
    LanguageModelProvider,
    ProviderResponseError,
    ProviderStructuredOutputError,
    ProviderTimeoutError,
)
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRequestAuthorityV1,
    EditorGenerationRuntimeAuthorityV1,
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_authority_v1.canonical import semantic_fingerprint
from pastila_scout.editor_generation_authority_v1.models import (
    _option_values,
    _options_semantics,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
    EditorGenerationProviderAdapterError,
    EditorNeutralLanguageModelProviderV1,
)
from pastila_scout.editor_generation_provider_adapter_v1.application_request import (
    _EditorGenerationApplicationRequestBuilderV1,
)
from pastila_scout.editor_generation_provider_adapter_v1.errors import (
    ProviderCancellationError,
)
from pastila_scout.editor_request_fingerprint_authority_v1 import (
    EditorRequestFingerprintAuthorityV1,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_selection_v1 import (
    ProviderChoiceV1,
    ProviderExecutorRegistrationV1,
    ProviderSelectionConfigV1,
    ProviderSelectorV1,
)
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
)
from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeExecutionBridgeV1,
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)
from pastila_scout.scout_runtime_v1 import (
    ScoutCancellationV1,
    ScoutRuntimeCompositionV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)
from pastila_scout.scout_workflow_execution_v1 import ScoutWorkflowExecutionV1

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
VALID = '{"bridge_text":"Salut","declared_plan_references":[],"warnings":[]}'


@dataclass
class Executor:
    text: str = VALID
    outcome: ExecutionOutcomeV2 = ExecutionOutcomeV2.COMPLETED
    calls: list[ProviderExecutionRequestV2] = field(default_factory=list)

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.calls.append(request)
        if self.outcome is ExecutionOutcomeV2.COMPLETED:
            result = ProviderResultProjectionV2(
                status=ProviderResultStatusV2.SUCCESS,
                outputs=(
                    ProviderOutputInputV2(
                        source_request_reference=request.request_envelope.request_units[
                            0
                        ].source_request_reference,
                        ordinal=0,
                        generated_text=self.text,
                        finish_reason=ProviderFinishReasonV2.COMPLETED,
                    ),
                ),
            )
            return ProviderExecutionResultV2(
                request_id=request.context.request_id,
                provider_id=request.provider.provider_id,
                request_envelope_identity=request.request_envelope.identity,
                outcome=self.outcome,
                finished_at=NOW,
                provider_result=result,
            )
        return ProviderExecutionResultV2(
            request_id=request.context.request_id,
            provider_id=request.provider.provider_id,
            request_envelope_identity=request.request_envelope.identity,
            outcome=self.outcome,
            finished_at=NOW,
            failure_code="safe-failure",
        )


class Legacy:
    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        raise AssertionError(request)


class Clock:
    def now(self) -> datetime:
        return NOW


class Cancellation:
    def __init__(self, requested: bool = False):
        self.requested = requested

    def snapshot(self) -> CancellationTokenV2:
        return CancellationTokenV2(cancellation_requested=self.requested)


class References:
    def __init__(self):
        self.calls = []

    def create(self, *, prompt_fingerprint: str, attempt_number: int) -> str:
        self.calls.append((prompt_fingerprint, attempt_number))
        return f"editor-operation-attempt-{attempt_number}"


class Recorder:
    def __init__(self):
        self.items = []

    def record(self, observation: EditorGenerationAttemptObservationV1) -> None:
        self.items.append(copy.copy(observation))

    def snapshot(self) -> tuple[EditorGenerationAttemptObservationV1, ...]:
        return tuple(copy.copy(item) for item in self.items)


def options(provider: ProviderChoiceV1):
    model = "gpt-4.1-mini" if provider is ProviderChoiceV1.OPENAI else "qwen3:14b"
    return EditorGenerationRuntimeOptionsV1(
        provider,
        model,
        None,
        0.3,
        1.0,
        500,
        None,
        (),
        True,
        TimeoutPolicyV2(timeout_seconds=30.0),
    )


def runtime(provider: ProviderChoiceV1):
    selected = options(provider)
    reference = f"editor-runtime-{provider.value}"
    fingerprint = semantic_fingerprint(
        {
            "options": _options_semantics(_option_values(selected)),
            "runtime_reference": reference,
        }
    )
    return EditorGenerationRuntimeAuthorityV1(selected, reference, fingerprint)


def config(provider: ProviderChoiceV1):
    selected = options(provider)
    return LanguageGenerationConfig(
        provider=provider.value,
        model_identifier=selected.model_identifier,
        model_revision=None,
        temperature=0.3,
        top_p=1.0,
        max_output_tokens=500,
        seed=None,
        structured_output_mode=True,
        timeout_seconds=30.0,
    )


def prompt():
    return GenerationPrompt(
        component_type="call_to_action",
        sections=(
            PromptSection(
                layer=PromptLayer.GENERATION_TASK,
                title="Task",
                content="Păstrează  exact\ntextul.",
            ),
        ),
        output_schema_name="CallToActionGenerationResult",
        prompt_fingerprint="sha256:" + "1" * 64,
    )


def workflow(provider, selected, unselected):
    other = (
        ProviderChoiceV1.OLLAMA
        if provider is ProviderChoiceV1.OPENAI
        else ProviderChoiceV1.OPENAI
    )
    selector = ProviderSelectorV1(
        ProviderSelectionConfigV1(provider=provider),
        (
            ProviderExecutorRegistrationV1(provider, selected),
            ProviderExecutorRegistrationV1(other, unselected),
        ),
    )
    composition = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("editor-provider-test"),
        ScoutRuntimeOptionsV1("editor-provider-options"),
        ScoutCancellationV1(False),
    )
    return ScoutWorkflowExecutionV1(
        Legacy(), ScoutRuntimeExecutionBridgeV1(composition)
    )


def adapter(provider=ProviderChoiceV1.OPENAI, selected=None, cancellation=None):
    selected = selected or Executor()
    unselected = Executor()
    recorder = Recorder()
    references = References()
    value = EditorNeutralLanguageModelProviderV1(
        provider=provider,
        workflow=workflow(provider, selected, unselected),
        runtime_authority=runtime(provider),
        fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
        request_authority=EditorGenerationRequestAuthorityV1(),
        requested_at_factory=Clock(),
        cancellation_source=cancellation or Cancellation(),
        request_reference_factory=references,
        attempt_recorder=recorder,
    )
    return value, selected, unselected, recorder, references


def test_exact_api_protocol_and_private_builder():
    assert api.__all__ == (
        "EditorGenerationAttemptObservationV1",
        "EditorGenerationProviderAdapterError",
        "EditorNeutralLanguageModelProviderV1",
    )
    assert not hasattr(api, "_EditorGenerationApplicationRequestBuilderV1")
    actual = inspect.signature(EditorNeutralLanguageModelProviderV1.generate_structured)
    frozen = inspect.signature(LanguageModelProvider.generate_structured)
    assert tuple(actual.parameters) == tuple(frozen.parameters)
    assert tuple(p.kind for p in actual.parameters.values()) == tuple(
        p.kind for p in frozen.parameters.values()
    )
    assert (
        "fingerprint"
        not in inspect.signature(
            _EditorGenerationApplicationRequestBuilderV1.build
        ).parameters
    )


@pytest.mark.parametrize("provider", list(ProviderChoiceV1))
def test_real_neutral_chain_selected_once(provider):
    value, selected, unselected, recorder, references = adapter(provider)
    result = value.generate_structured(
        prompt=prompt(),
        output_schema=CallToActionGenerationResult,
        config=config(provider),
    )
    assert (
        type(result) is CallToActionGenerationResult and result.bridge_text == "Salut"
    )
    assert len(selected.calls) == 1 and unselected.calls == []
    assert len(recorder.items) == 1 and references.calls == [
        (prompt().prompt_fingerprint, 1)
    ]
    assert (
        selected.calls[0].request_intent.request_units[0].messages[0].content
        == prompt().text
    )


def test_two_invocations_are_two_distinct_attempts_no_internal_retry():
    value, selected, _, recorder, references = adapter()
    for _ in range(2):
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OPENAI),
        )
    assert len(selected.calls) == 2
    assert [item.attempt_number for item in recorder.items] == [1, 2]
    assert [item[1] for item in references.calls] == [1, 2]
    assert recorder.items[0].request_reference != recorder.items[1].request_reference


@pytest.mark.parametrize(
    ("outcome", "error"),
    [
        (ExecutionOutcomeV2.TIMEOUT, ProviderTimeoutError),
        (ExecutionOutcomeV2.CANCELLED, ProviderCancellationError),
        (ExecutionOutcomeV2.PROVIDER_FAILURE, ProviderResponseError),
        (ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE, ProviderResponseError),
    ],
)
def test_failure_mapping_one_call(outcome, error):
    value, selected, unselected, recorder, _ = adapter(
        selected=Executor(outcome=outcome)
    )
    with pytest.raises(error):
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OPENAI),
        )
    assert (
        len(selected.calls) == 1 and unselected.calls == [] and len(recorder.items) == 1
    )


def test_predispatch_cancellation_zero_execution():
    value, selected, unselected, recorder, _ = adapter(cancellation=Cancellation(True))
    with pytest.raises(ProviderCancellationError):
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OPENAI),
        )
    assert selected.calls == unselected.calls == []
    assert recorder.items[0].outcome is ExecutionOutcomeV2.CANCELLED


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('{"bridge_text":', "malformed structured output"),
        ("[]", "failed schema validation"),
        (
            '{"bridge_text":"x","declared_plan_references":[1],"warnings":[]}',
            "failed schema validation",
        ),
        ("```json\n{}\n```", "malformed structured output"),
    ],
)
def test_strict_json_error_classification_no_repair(text, message):
    value, selected, _, _, _ = adapter(selected=Executor(text=text))
    with pytest.raises(ProviderStructuredOutputError, match=message):
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OPENAI),
        )
    assert len(selected.calls) == 1


@pytest.mark.parametrize(
    ("text", "failure_class"),
    [
        ('{"bridge_text":', "MALFORMED_JSON"),
        ("[]", "SCHEMA_VALIDATION_FAILED"),
    ],
)
def test_structured_failure_exposes_bounded_class_without_generated_text(
    text, failure_class
):
    value, _, _, _, _ = adapter(selected=Executor(text=text))
    with pytest.raises(ProviderStructuredOutputError) as caught:
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OPENAI),
        )
    diagnostic = str(caught.value)
    assert diagnostic.startswith(failure_class)
    assert text not in diagnostic
    assert len(diagnostic) <= 600


def frozen_models():
    block = CommentaryBlockResult(
        block_type="commentary",
        text="Text",
        sequence=1,
        source_fact_ids=("f",),
        blueprint_intent_ids=("e",),
        voice_plan_ids=("v",),
        satire_target_ids=(),
        protected_target_ids=(),
    )
    return (
        StoryGenerationResult(
            story_id=1,
            factual_summary="Summary",
            commentary_blocks=(block,),
            ending="End",
            ending_type="closed",
            declared_fact_usage=("f",),
            declared_editorial_intent_usage=("e",),
            declared_conversation_intent_usage=(),
            declared_voice_intent_usage=("v",),
        ),
        TransitionGenerationResult(
            from_story_id=1,
            to_story_id=2,
            text="Next",
            transition_type="bridge",
            declared_plan_references=("p",),
        ),
        OpeningGenerationResult(
            text="Open",
            referenced_story_ids=(1,),
            opening_mechanism="lead",
            declared_plan_references=("p",),
        ),
        ClosingGenerationResult(
            text="Close", closing_mechanism="callback", declared_plan_references=("p",)
        ),
        CallToActionGenerationResult(
            bridge_text="Support", declared_plan_references=("p",)
        ),
    )


@pytest.mark.parametrize("model", frozen_models())
def test_all_frozen_tuple_models_accept_strict_json(model):
    rebuilt = type(model).model_validate_json(model.model_dump_json(), strict=True)
    assert type(rebuilt) is type(model) and rebuilt == model


def test_empty_nonempty_nested_and_wrong_types():
    empty = CallToActionGenerationResult.model_validate_json(VALID, strict=True)
    nonempty = CallToActionGenerationResult.model_validate_json(
        '{"bridge_text":"x","declared_plan_references":["p"],"warnings":["w"]}',
        strict=True,
    )
    story = frozen_models()[0]
    nested = StoryGenerationResult.model_validate_json(
        story.model_dump_json(), strict=True
    )
    assert (
        empty.declared_plan_references == ()
        and nonempty.declared_plan_references == ("p",)
    )
    assert (
        type(nested.commentary_blocks) is tuple
        and type(nested.commentary_blocks[0].source_fact_ids) is tuple
    )
    with pytest.raises(ValidationError):
        CallToActionGenerationResult.model_validate_json(
            '{"bridge_text":"x","declared_plan_references":[1],"warnings":[]}',
            strict=True,
        )


def test_invalid_config_and_dependency_execute_zero():
    value, selected, unselected, _, _ = adapter()
    with pytest.raises(ProviderResponseError):
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OLLAMA),
        )
    assert selected.calls == unselected.calls == []
    with pytest.raises(EditorGenerationProviderAdapterError):
        EditorNeutralLanguageModelProviderV1(
            provider=ProviderChoiceV1.OPENAI,
            workflow=object(),
            runtime_authority=runtime(ProviderChoiceV1.OPENAI),
            fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
            request_authority=EditorGenerationRequestAuthorityV1(),
            requested_at_factory=Clock(),
            cancellation_source=Cancellation(),
            request_reference_factory=References(),
            attempt_recorder=Recorder(),
        )


def test_object_safety_and_passivity():
    value, selected, unselected, recorder, references = adapter()
    assert repr(value) == "EditorNeutralLanguageModelProviderV1(<injected authorities>)"
    assert not hasattr(value, "__dict__")
    assert copy.copy(value) == value and copy.deepcopy(value) == value
    with pytest.raises(TypeError, match="does not support pickle"):
        pickle.dumps(value)
    assert (
        selected.calls == unselected.calls == recorder.items == references.calls == []
    )


def test_single_strict_json_call_and_exact_text(monkeypatch):
    raw = '\n {"bridge_text":"Salut","declared_plan_references":[],"warnings":[]} \n'
    value, _, _, _, _ = adapter(selected=Executor(text=raw))
    original = CallToActionGenerationResult.model_validate_json
    calls = []

    def validate(cls, json_data, *, strict=None, **kwargs):
        calls.append((json_data, strict, kwargs))
        return original(json_data, strict=strict, **kwargs)

    monkeypatch.setattr(
        CallToActionGenerationResult, "model_validate_json", classmethod(validate)
    )
    result = value.generate_structured(
        prompt=prompt(),
        output_schema=CallToActionGenerationResult,
        config=config(ProviderChoiceV1.OPENAI),
    )
    assert type(result) is CallToActionGenerationResult
    assert calls == [(raw, True, {})]


def test_authorities_and_builder_called_once(monkeypatch):
    counts = {"fingerprint": 0, "builder": 0, "request": 0}
    fingerprint = EditorRequestFingerprintAuthorityV1.fingerprint
    builder = _EditorGenerationApplicationRequestBuilderV1.build
    request = EditorGenerationRequestAuthorityV1.build

    def count_fingerprint(self, **kwargs):
        counts["fingerprint"] += 1
        return fingerprint(self, **kwargs)

    def count_builder(self, **kwargs):
        counts["builder"] += 1
        return builder(self, **kwargs)

    def count_request(self, source, runtime_authority):
        counts["request"] += 1
        return request(self, source, runtime_authority)

    monkeypatch.setattr(
        EditorRequestFingerprintAuthorityV1, "fingerprint", count_fingerprint
    )
    monkeypatch.setattr(
        _EditorGenerationApplicationRequestBuilderV1, "build", count_builder
    )
    monkeypatch.setattr(EditorGenerationRequestAuthorityV1, "build", count_request)
    value, selected, _, _, _ = adapter()
    value.generate_structured(
        prompt=prompt(),
        output_schema=CallToActionGenerationResult,
        config=config(ProviderChoiceV1.OPENAI),
    )
    assert counts == {"fingerprint": 1, "builder": 1, "request": 1}
    assert len(selected.calls) == 1


def test_errors_have_no_cause_or_context():
    value, _, _, _, _ = adapter(selected=Executor(text="{"))
    with pytest.raises(ProviderStructuredOutputError) as caught:
        value.generate_structured(
            prompt=prompt(),
            output_schema=CallToActionGenerationResult,
            config=config(ProviderChoiceV1.OPENAI),
        )
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.__suppress_context__ is True


def test_forbidden_parsing_and_dependency_imports_are_absent():
    package = Path(api.__file__).parent
    assert sorted(item.name for item in package.iterdir() if item.is_file()) == [
        "__init__.py",
        "adapter.py",
        "application_request.py",
        "errors.py",
        "models.py",
        "parsing.py",
        "protocols.py",
    ]
    source = "\n".join(
        item.read_text(encoding="utf-8") for item in package.glob("*.py")
    )
    assert "json.loads" not in source
    assert "model_validate(parsed" not in source
    assert "editor_generation_execution_v1" not in source
    assert "provider_execution_openai" not in source
    assert "provider_execution_ollama" not in source


class DynamicClock:
    def __getattr__(self, name):
        raise AttributeError(name)

    def now(self) -> datetime:
        return NOW


def test_dynamic_dependency_is_rejected_without_execution():
    selected, unselected = Executor(), Executor()
    with pytest.raises(EditorGenerationProviderAdapterError):
        EditorNeutralLanguageModelProviderV1(
            provider=ProviderChoiceV1.OPENAI,
            workflow=workflow(ProviderChoiceV1.OPENAI, selected, unselected),
            runtime_authority=runtime(ProviderChoiceV1.OPENAI),
            fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
            request_authority=EditorGenerationRequestAuthorityV1(),
            requested_at_factory=DynamicClock(),
            cancellation_source=Cancellation(),
            request_reference_factory=References(),
            attempt_recorder=Recorder(),
        )
    assert selected.calls == unselected.calls == []
