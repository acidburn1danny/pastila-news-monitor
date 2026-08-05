"""Adversarial tests for generation-capable application authority."""

from __future__ import annotations

import copy
import json
import pickle
import subprocess
import sys
from datetime import UTC, datetime

import pytest

import pastila_scout.editor_generation_authority_v1 as authority_api
import pastila_scout.editor_generation_execution_v1 as execution_api
from pastila_scout.contracts.samples import (
    sample_episode_context,
    sample_scout_input,
    sample_selection_profile,
)
from pastila_scout.editor import SelectionEngine
from pastila_scout.editor.blueprint_builder import EditorialBlueprintBuilder
from pastila_scout.editor.commentary_builder import CommentaryBlueprintBuilder
from pastila_scout.editor.engine import EditorialSelectionResult
from pastila_scout.editor.flow_optimizer import EpisodeFlowOptimizer
from pastila_scout.editor.generation.models import (
    LanguageGenerationConfig,
    StoryGenerationResult,
)
from pastila_scout.editor.voice_builder import VoiceModelBuilder
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationApplicationRequestV1,
    EditorGenerationAuthorityError,
    EditorGenerationRequestAuthorityV1,
    EditorGenerationRuntimeAuthorityV1,
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_schema,
    semantic_fingerprint,
)
from pastila_scout.editor_generation_authority_v1.models import (
    _option_values,
    _options_semantics,
    _request_semantics,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_generation_execution_v1.models import _semantics
from pastila_scout.editor_operational_v1 import EditorOperationalCoordinatorV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

AUTHORITY_API = (
    "EditorGenerationApplicationRequestV1",
    "EditorGenerationAuthorityError",
    "EditorGenerationRequestAuthorityV1",
    "EditorGenerationRuntimeAuthorityV1",
    "EditorGenerationRuntimeOptionsV1",
)


def options(provider=ProviderChoiceV1.OPENAI, **changes):
    values = {
        "provider": provider,
        "model_identifier": "model-v1",
        "model_revision": None,
        "temperature": 0.3,
        "top_p": 1.0,
        "max_output_tokens": 2000,
        "seed": None,
        "stop_sequences": (),
        "structured_output_mode": True,
        "timeout_policy": TimeoutPolicyV2(timeout_seconds=30.0),
    }
    values.update(changes)
    return EditorGenerationRuntimeOptionsV1(**values)


def application(runtime_options=None):
    selected = runtime_options or options()
    schema_json, schema_hash = canonical_schema(
        StoryGenerationResult.model_json_schema()
    )
    values = (
        selected.provider,
        "Prompt exact",
        "editor-request-1",
        datetime(2026, 8, 5, 12, tzinfo=UTC),
        selected,
        "StoryGenerationResult",
        schema_json,
        schema_hash,
        CancellationTokenV2(cancellation_requested=False),
    )
    return EditorGenerationApplicationRequestV1(
        *values, semantic_fingerprint(_request_semantics(values))
    )


def runtime(runtime_options=None):
    selected = runtime_options or options()
    reference = "editor-runtime-1"
    fingerprint = semantic_fingerprint(
        {
            "options": _options_semantics(_option_values(selected)),
            "runtime_reference": reference,
        }
    )
    return EditorGenerationRuntimeAuthorityV1(selected, reference, fingerprint)


def execution_request():
    source = sample_scout_input()
    profile = sample_selection_profile()
    context = sample_episode_context()
    preparation = EditorOperationalCoordinatorV1(SelectionEngine()).prepare(
        source, profile, context
    )
    assert preparation.plan is not None
    plan = preparation.plan
    selection = EditorialSelectionResult(plan.selection_output, plan.selection_trace)
    flow = EpisodeFlowOptimizer().optimize(source, profile, context, selection)
    editorial = (
        EditorialBlueprintBuilder().build(source, profile, context, flow).blueprint
    )
    commentary = (
        CommentaryBlueprintBuilder()
        .build(source, profile, context, flow, editorial)
        .blueprint
    )
    voice = (
        VoiceModelBuilder()
        .build(source, profile, context, flow, editorial, commentary)
        .plan
    )
    config = LanguageGenerationConfig(
        provider="openai",
        model_identifier="model-v1",
        model_revision=None,
        temperature=0.3,
        top_p=1.0,
        max_output_tokens=2000,
        seed=None,
        structured_output_mode=True,
        timeout_seconds=30.0,
    )
    selected = options()
    values = (
        preparation,
        plan,
        flow,
        editorial,
        commentary,
        voice,
        config,
        selected,
        ProviderChoiceV1.OPENAI,
        datetime(2026, 8, 5, 12, tzinfo=UTC),
        "execution-request-1",
        CancellationTokenV2(cancellation_requested=False),
    )
    return EditorGenerationExecutionRequestV1(
        *values, semantic_fingerprint(_semantics(values))
    )


def test_exact_public_apis() -> None:
    assert authority_api.__all__ == AUTHORITY_API
    assert execution_api.__all__ == ("EditorGenerationExecutionRequestV1",)


def test_options_preserve_exact_generation_configuration() -> None:
    value = options()
    assert type(value.temperature) is float
    assert type(value.top_p) is float
    assert value.max_output_tokens == 2000
    assert value.seed is None
    assert value.stop_sequences == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"top_p": 0.9},
        {"seed": 7},
        {"stop_sequences": ("stop",)},
        {"structured_output_mode": False},
        {"temperature": True},
        {"max_output_tokens": True},
    ],
)
def test_unsupported_or_coerced_options_fail_closed(changes) -> None:
    with pytest.raises(EditorGenerationAuthorityError) as caught:
        options(**changes)
    assert str(caught.value) == "Editor generation authority is invalid."
    assert caught.value.__cause__ is None


def test_schema_authority_is_canonical_and_deterministic() -> None:
    first = application()
    second = application()
    assert first == second
    assert (
        json.dumps(
            json.loads(first.output_schema_canonical_json),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        == first.output_schema_canonical_json
    )
    assert len(first.output_schema_fingerprint) == 64


def test_lower_request_preserves_prompt_timeout_cancellation_and_lineage() -> None:
    source = application()
    lower = EditorGenerationRequestAuthorityV1().build(source, runtime())
    message = lower.request_intent.request_units[0].messages[0]
    assert message.role == "generation"
    assert message.content == source.prompt
    assert lower.timeout_policy == source.options.timeout_policy
    assert lower.context.cancellation == source.cancellation
    assert lower.request_intent.execution_plan_reference.startswith(
        "application-execution-plan-v1:"
    )


def test_raw_decomposed_prompt_is_preserved_then_lowered_to_nfc() -> None:
    selected = options()
    schema_json, schema_hash = canonical_schema(
        StoryGenerationResult.model_json_schema()
    )
    prompt = "A\u0306sta"
    values = (
        selected.provider,
        prompt,
        "editor-request-unicode",
        datetime(2026, 8, 5, 12, tzinfo=UTC),
        selected,
        "StoryGenerationResult",
        schema_json,
        schema_hash,
        CancellationTokenV2(cancellation_requested=False),
    )
    source = EditorGenerationApplicationRequestV1(
        *values, semantic_fingerprint(_request_semantics(values))
    )
    lower = EditorGenerationRequestAuthorityV1().build(source, runtime())

    assert source.prompt == prompt
    assert lower.request_intent.request_units[0].messages[0].content == "Ăsta"


def test_runtime_mismatch_fails_before_lower_construction() -> None:
    with pytest.raises(EditorGenerationAuthorityError):
        EditorGenerationRequestAuthorityV1().build(
            application(), runtime(options(ProviderChoiceV1.OLLAMA))
        )


def test_execution_request_reconstructs_all_artifacts_and_is_deterministic() -> None:
    first = execution_request()
    second = copy.copy(first)
    assert first == second and first is not second
    assert first.plan == first.preparation.plan
    assert first.editorial_blueprint.flow_order == first.voice_plan.flow_order
    assert first.request_fingerprint == second.request_fingerprint


def test_copied_invalid_and_pickle_fail_closed() -> None:
    value = application()
    object.__setattr__(value, "request_fingerprint", "0" * 64)
    with pytest.raises(EditorGenerationAuthorityError):
        copy.copy(value)
    with pytest.raises(TypeError):
        pickle.dumps(options())
    with pytest.raises(TypeError):
        pickle.dumps(execution_request())


def test_repr_is_content_safe_and_address_free() -> None:
    value = application()
    rendered = repr(value)
    assert "Prompt exact" not in rendered
    assert "0x" not in rendered
    assert "redacted" in rendered


def test_invalid_authority_traceback_retains_no_input_in_package_frames() -> None:
    secret = "TRACEBACK_SECRET_914"
    with pytest.raises(EditorGenerationAuthorityError) as caught:
        options(model_identifier=secret, temperature=True)
    traceback = caught.value.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename.replace("/", "\\")
        if "\\src\\pastila_scout\\editor_generation_authority_v1\\" in filename:
            assert secret not in traceback.tb_frame.f_locals.values()
        traceback = traceback.tb_next
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_imports_are_passive_in_fresh_process() -> None:
    script = "import pastila_scout.editor_generation_authority_v1; import pastila_scout.editor_generation_execution_v1"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""
