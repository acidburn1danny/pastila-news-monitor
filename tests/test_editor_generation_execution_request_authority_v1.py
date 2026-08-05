"""Focused adversarial coverage for aggregate execution-request authority."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import os
import pickle
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

import pastila_scout.editor_generation_execution_request_authority_v1 as api
import pastila_scout.editor_generation_execution_request_authority_v1.authority as implementation
import pastila_scout.editor_generation_execution_request_authority_v1.canonical as canonical_implementation
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
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.voice_builder import VoiceModelBuilder
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_execution_request_authority_v1 import (
    EditorGenerationExecutionRequestAuthorityError,
    EditorGenerationExecutionRequestAuthorityV1,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_operational_v1 import EditorOperationalCoordinatorV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

PUBLIC_API = (
    "EditorGenerationExecutionRequestAuthorityError",
    "EditorGenerationExecutionRequestAuthorityV1",
)


@pytest.fixture(scope="module")
def semantic_values():
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
    options = EditorGenerationRuntimeOptionsV1(
        ProviderChoiceV1.OPENAI,
        "model-v1",
        None,
        0.3,
        1.0,
        2000,
        None,
        (),
        True,
        TimeoutPolicyV2(timeout_seconds=30.0),
    )
    configuration = LanguageGenerationConfig(
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
    return (
        preparation,
        plan,
        flow,
        editorial,
        commentary,
        voice,
        configuration,
        options,
        ProviderChoiceV1.OPENAI,
        datetime(2026, 8, 5, 12, tzinfo=UTC),
        "execution-request-1",
        CancellationTokenV2(cancellation_requested=False),
    )


def construct(values):
    return EditorGenerationExecutionRequestAuthorityV1().construct(
        preparation=values[0],
        plan=values[1],
        flow_result=values[2],
        editorial_blueprint=values[3],
        commentary_blueprint=values[4],
        voice_plan=values[5],
        generation_configuration=values[6],
        runtime_options=values[7],
        provider=values[8],
        requested_at=values[9],
        request_reference=values[10],
        cancellation=values[11],
    )


def alternate_preparation():
    profile = sample_selection_profile()
    payload = profile.model_dump(mode="python", warnings=False)
    payload["profile_name"] = "alternate-profile"
    alternate = type(profile).model_validate(payload, strict=True)
    return EditorOperationalCoordinatorV1(SelectionEngine()).prepare(
        sample_scout_input(), alternate, sample_episode_context()
    )


def alternate_flow_and_editorial(*, target_story_count=None):
    source = sample_scout_input()
    profile = sample_selection_profile()
    payload = profile.model_dump(mode="python", warnings=False)
    payload["profile_name"] = "alternate-profile"
    if target_story_count is not None:
        payload["target_story_count"] = target_story_count
    alternate = type(profile).model_validate(payload, strict=True)
    context = sample_episode_context()
    preparation = EditorOperationalCoordinatorV1(SelectionEngine()).prepare(
        source, alternate, context
    )
    assert preparation.plan is not None
    plan = preparation.plan
    selection = EditorialSelectionResult(plan.selection_output, plan.selection_trace)
    flow = EpisodeFlowOptimizer().optimize(source, alternate, context, selection)
    editorial = (
        EditorialBlueprintBuilder().build(source, alternate, context, flow).blueprint
    )
    return flow, editorial


def invalid_request(values, *, fingerprint="0" * 64):
    request = object.__new__(EditorGenerationExecutionRequestV1)
    for name, value in zip(implementation._FIELD_NAMES, values, strict=True):
        object.__setattr__(request, name, value)
    object.__setattr__(request, "request_fingerprint", fingerprint)
    return request


def replace_nested(value, old, new):
    if type(value) in {str, int}:
        return new if value == old else value
    if type(value) is tuple:
        return tuple(replace_nested(item, old, new) for item in value)
    if type(value) is list:
        return [replace_nested(item, old, new) for item in value]
    if type(value) is dict:
        return {key: replace_nested(item, old, new) for key, item in value.items()}
    return value


def test_exact_package_api_and_signatures() -> None:
    assert api.__all__ == PUBLIC_API
    assert (
        set(vars(api))
        & {
            "canonical_value",
            "request_projection",
            "request_fingerprint",
        }
        == set()
    )
    constructor = inspect.signature(EditorGenerationExecutionRequestAuthorityV1)
    assert tuple(constructor.parameters) == ()
    construct_signature = inspect.signature(
        EditorGenerationExecutionRequestAuthorityV1.construct
    )
    assert tuple(construct_signature.parameters) == (
        "self",
        "preparation",
        "plan",
        "flow_result",
        "editorial_blueprint",
        "commentary_blueprint",
        "voice_plan",
        "generation_configuration",
        "runtime_options",
        "provider",
        "requested_at",
        "request_reference",
        "cancellation",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in tuple(construct_signature.parameters.values())[1:]
    )
    assert tuple(
        inspect.signature(
            EditorGenerationExecutionRequestAuthorityV1.reconstruct
        ).parameters
    ) == ("self", "request")


def test_construct_and_reconstruct_nominally(semantic_values) -> None:
    request = construct(semantic_values)
    rebuilt = EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    assert type(request) is EditorGenerationExecutionRequestV1
    assert type(rebuilt) is EditorGenerationExecutionRequestV1
    assert rebuilt is not request
    assert rebuilt == request
    assert len(request.request_fingerprint) == 64


def test_construct_exact_cardinality(monkeypatch, semantic_values) -> None:
    counts = {"projection": 0, "fingerprint": 0, "constructor": 0, "copy": 0}
    original_projection = implementation.request_projection
    original_fingerprint = implementation.request_fingerprint
    original_constructor = implementation._frozen_construct
    original_copy = implementation.copy.copy

    def projection(values):
        counts["projection"] += 1
        return original_projection(values)

    def fingerprint(value):
        counts["fingerprint"] += 1
        return original_fingerprint(value)

    def constructor(values, fingerprint):
        counts["constructor"] += 1
        return original_constructor(values, fingerprint)

    def public_copy(value):
        if type(value) is EditorGenerationExecutionRequestV1:
            counts["copy"] += 1
        return original_copy(value)

    monkeypatch.setattr(implementation, "request_projection", projection)
    monkeypatch.setattr(implementation, "request_fingerprint", fingerprint)
    monkeypatch.setattr(implementation, "_frozen_construct", constructor)
    monkeypatch.setattr(implementation.copy, "copy", public_copy)
    request = construct(semantic_values)
    assert type(request) is EditorGenerationExecutionRequestV1
    assert counts == {"projection": 1, "fingerprint": 1, "constructor": 1, "copy": 1}


def test_reconstruct_exact_cardinality(monkeypatch, semantic_values) -> None:
    request = construct(semantic_values)
    counts = {"projection": 0, "fingerprint": 0, "copy": 0}
    original_projection = implementation.request_projection
    original_fingerprint = implementation.request_fingerprint
    original_copy = implementation.copy.copy

    def projection(values):
        counts["projection"] += 1
        return original_projection(values)

    def fingerprint(value):
        counts["fingerprint"] += 1
        return original_fingerprint(value)

    def public_copy(value):
        if type(value) is EditorGenerationExecutionRequestV1:
            counts["copy"] += 1
        return original_copy(value)

    monkeypatch.setattr(implementation, "request_projection", projection)
    monkeypatch.setattr(implementation, "request_fingerprint", fingerprint)
    monkeypatch.setattr(implementation.copy, "copy", public_copy)
    rebuilt = EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    assert rebuilt == request
    assert counts == {"projection": 1, "fingerprint": 1, "copy": 1}


def test_construct_exact_stage_order(monkeypatch, semantic_values) -> None:
    events = []
    originals = {
        name: getattr(implementation, name)
        for name in (
            "_reconstruct_values",
            "_configuration_is_valid",
            "_lineage_is_valid",
            "request_projection",
            "request_fingerprint",
            "_frozen_construct",
            "_semantic_match",
        )
    }
    original_copy = implementation.copy.copy

    def wrap(name, event):
        def operation(*args, **kwargs):
            events.append(event)
            return originals[name](*args, **kwargs)

        return operation

    for name, event in (
        ("_reconstruct_values", "semantic_reconstructions"),
        ("_configuration_is_valid", "configuration_parity"),
        ("_lineage_is_valid", "lineage"),
        ("request_projection", "projection"),
        ("request_fingerprint", "fingerprint"),
        ("_frozen_construct", "frozen_construction"),
        ("_semantic_match", "semantic_parity"),
    ):
        monkeypatch.setattr(implementation, name, wrap(name, event))

    def public_copy(value):
        if type(value) is EditorGenerationExecutionRequestV1:
            events.append("public_copy")
        return original_copy(value)

    monkeypatch.setattr(implementation.copy, "copy", public_copy)
    construct(semantic_values)
    assert events == [
        "semantic_reconstructions",
        "configuration_parity",
        "lineage",
        "projection",
        "fingerprint",
        "frozen_construction",
        "public_copy",
        "semantic_parity",
    ]


def test_reconstruct_exact_stage_order(monkeypatch, semantic_values) -> None:
    request = construct(semantic_values)
    events = []
    originals = {
        name: getattr(implementation, name)
        for name in (
            "_extract",
            "_reconstruct_values",
            "_configuration_is_valid",
            "_lineage_is_valid",
            "request_projection",
            "request_fingerprint",
            "_semantic_match",
        )
    }
    original_copy = implementation.copy.copy

    def wrap(name, event):
        def operation(*args, **kwargs):
            events.append(event)
            return originals[name](*args, **kwargs)

        return operation

    for name, event in (
        ("_extract", "field_extraction"),
        ("_reconstruct_values", "semantic_reconstructions"),
        ("_configuration_is_valid", "configuration_parity"),
        ("_lineage_is_valid", "lineage"),
        ("request_projection", "projection"),
        ("request_fingerprint", "fingerprint"),
        ("_semantic_match", "semantic_parity"),
    ):
        monkeypatch.setattr(implementation, name, wrap(name, event))

    def public_copy(value):
        if type(value) is EditorGenerationExecutionRequestV1:
            events.append("public_copy")
        return original_copy(value)

    monkeypatch.setattr(implementation.copy, "copy", public_copy)
    EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    assert events == [
        "field_extraction",
        "semantic_reconstructions",
        "configuration_parity",
        "lineage",
        "projection",
        "fingerprint",
        "public_copy",
        "semantic_parity",
    ]


def test_configuration_precedes_lineage_in_both_paths(
    monkeypatch, semantic_values
) -> None:
    values = list(semantic_values)
    alternate = alternate_preparation()
    assert alternate.plan is not None
    values[1] = alternate.plan
    values[8] = ProviderChoiceV1.OLLAMA
    canonical_calls = 0

    def projection(values):
        nonlocal canonical_calls
        del values
        canonical_calls += 1

    monkeypatch.setattr(implementation, "request_projection", projection)
    status, _ = implementation._construct(tuple(values))
    assert status is implementation._Status.INVALID_CONFIGURATION_PARITY
    request = invalid_request(tuple(values))
    status, _ = implementation._reconstruct(request)
    assert status is implementation._Status.INVALID_CONFIGURATION_PARITY
    assert canonical_calls == 0


@pytest.mark.parametrize("index", range(12))
def test_wrong_exact_semantic_type_fails_closed(semantic_values, index) -> None:
    values = list(semantic_values)
    values[index] = object()
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        construct(tuple(values))
    assert str(caught.value) == (
        "Editor generation execution request authority is invalid."
    )
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.__suppress_context__ is True


def test_configuration_and_provider_mismatch_fail(semantic_values) -> None:
    values = list(semantic_values)
    values[8] = ProviderChoiceV1.OLLAMA
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        construct(tuple(values))


@pytest.mark.parametrize(
    "case", ("plan", "flow", "editorial", "commentary", "voice", "order")
)
def test_real_lineage_failures_stop_before_canonicalization(
    monkeypatch, semantic_values, case
) -> None:
    values = list(semantic_values)
    if case == "plan":
        alternate = alternate_preparation()
        assert alternate.plan is not None
        values[1] = alternate.plan
    elif case == "flow":
        values[2], _ = alternate_flow_and_editorial()
    elif case in {"editorial", "commentary", "voice"}:
        index = {"editorial": 3, "commentary": 4, "voice": 5}[case]
        values[index] = values[index].model_copy(
            update={"source_report_id": "changed-report"}
        )
    else:
        original = values[3].flow_order[0]
        replacement = 45 if original != 45 else 46
        payload = replace_nested(
            values[3].model_dump(mode="python", warnings=False),
            original,
            replacement,
        )
        values[3] = type(values[3]).model_validate(payload, strict=True)
    later = []
    monkeypatch.setattr(
        implementation,
        "request_projection",
        lambda values: later.append("canonicalization"),
    )
    monkeypatch.setattr(
        implementation,
        "_frozen_construct",
        lambda values, fingerprint: later.append("frozen"),
    )
    status, result = implementation._construct(tuple(values))
    assert status is implementation._Status.INVALID_LINEAGE
    assert result is None
    assert later == []
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        construct(tuple(values))


@pytest.mark.parametrize("case", ("provider", "model", "timeout"))
def test_real_configuration_failures_stop_before_lineage(
    monkeypatch, semantic_values, case
) -> None:
    values = list(semantic_values)
    if case == "provider":
        values[8] = ProviderChoiceV1.OLLAMA
    elif case == "model":
        values[6] = values[6].model_copy(update={"model_identifier": "changed-model"})
    else:
        values[6] = values[6].model_copy(update={"timeout_seconds": 31.0})
    later = []
    monkeypatch.setattr(
        implementation,
        "_lineage_is_valid",
        lambda *values: later.append("lineage"),
    )
    monkeypatch.setattr(
        implementation,
        "request_projection",
        lambda values: later.append("canonicalization"),
    )
    status, result = implementation._construct(tuple(values))
    assert status is implementation._Status.INVALID_CONFIGURATION_PARITY
    assert result is None
    assert later == []


@pytest.mark.parametrize(
    ("index", "attribute"),
    [
        (0, "plan"),
        (1, "source_report_id"),
        (2, "output"),
        (3, "flow_order"),
        (4, "flow_order"),
        (5, "flow_order"),
        (6, "provider"),
        (7, "model_identifier"),
        (11, "cancellation_requested"),
    ],
)
def test_copied_invalid_semantic_state_fails(semantic_values, index, attribute) -> None:
    values = list(semantic_values)
    invalid = copy.copy(values[index])
    object.__setattr__(invalid, attribute, object())
    values[index] = invalid
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        construct(tuple(values))


def test_copied_invalid_nested_state_fails(semantic_values) -> None:
    values = list(semantic_values)
    invalid_options = copy.copy(values[7])
    object.__setattr__(invalid_options, "model_identifier", "changed")
    values[7] = invalid_options
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        construct(tuple(values))


def test_copied_invalid_request_and_forged_fingerprint_fail(semantic_values) -> None:
    request = construct(semantic_values)
    object.__setattr__(request, "request_fingerprint", "0" * 64)
    status, result = implementation._reconstruct(request)
    assert status is implementation._Status.FINGERPRINT_MISMATCH
    assert result is None
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    _assert_recursive_authority_isolation(caught.value, (*semantic_values, request))


def test_request_subclass_and_authority_subclass_are_rejected(semantic_values) -> None:
    class RequestSubclass(EditorGenerationExecutionRequestV1):
        pass

    class AuthoritySubclass(EditorGenerationExecutionRequestAuthorityV1):
        pass

    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        AuthoritySubclass()
    request = object.__new__(RequestSubclass)
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)


def test_unicode_and_timezone_canonical_equivalence(semantic_values) -> None:
    first = list(semantic_values)
    second = list(semantic_values)
    first[10] = "cerere-ă"
    second[10] = "cerere-ă"
    first[9] = datetime(2026, 8, 5, 12, tzinfo=UTC)
    second[9] = datetime(2026, 8, 5, 15, tzinfo=timezone(timedelta(hours=3)))
    assert (
        construct(tuple(first)).request_fingerprint
        == construct(tuple(second)).request_fingerprint
    )


def test_semantic_mutation_changes_fingerprint(semantic_values) -> None:
    first = construct(semantic_values)
    changed = list(semantic_values)
    changed[10] = "execution-request-2"
    second = construct(tuple(changed))
    assert first.request_fingerprint != second.request_fingerprint


@pytest.mark.parametrize("index", range(12))
def test_each_semantic_field_changes_aggregate_fingerprint(
    semantic_values, index
) -> None:
    baseline = tuple(semantic_values)
    changed = list(baseline)
    alternate = alternate_preparation()
    assert alternate.plan is not None
    if index == 0:
        changed[index] = alternate
    elif index == 1:
        changed[index] = alternate.plan
    elif index == 2:
        candidate = copy.copy(baseline[index])
        object.__setattr__(candidate, "trace", ("changed",))
        changed[index] = candidate
    elif index in {3, 4, 5}:
        changed[index] = baseline[index].model_copy(
            update={"source_report_id": "changed-report"}
        )
    elif index == 6:
        changed[index] = baseline[index].model_copy(
            update={"model_identifier": "changed-model"}
        )
    elif index == 7:
        candidate = copy.copy(baseline[index])
        object.__setattr__(candidate, "model_identifier", "changed-model")
        changed[index] = candidate
    elif index == 8:
        changed[index] = ProviderChoiceV1.OLLAMA
    elif index == 9:
        changed[index] = baseline[index] + timedelta(seconds=1)
    elif index == 10:
        changed[index] = "changed-reference"
    else:
        changed[index] = baseline[index].model_copy(
            update={"cancellation_requested": True}
        )
    first = canonical_implementation.request_fingerprint(
        canonical_implementation.request_projection(baseline)
    )
    second = canonical_implementation.request_fingerprint(
        canonical_implementation.request_projection(tuple(changed))
    )
    assert first != second
    assert all(
        changed[position] is baseline[position]
        for position in range(12)
        if position != index
    )


def test_numeric_boolean_and_ordering_semantics_are_exact() -> None:
    assert canonical_implementation.tagged_number(1) == {
        "type": "int",
        "value": 1,
    }
    assert canonical_implementation.tagged_number(1.0) == {
        "type": "float",
        "value": 1.0,
    }
    with pytest.raises(TypeError):
        canonical_implementation.tagged_number(True)
    assert canonical_implementation.canonical_value(True) is True
    assert canonical_implementation.canonical_value(1) == 1
    assert type(canonical_implementation.canonical_value(True)) is bool
    assert type(canonical_implementation.canonical_value(1)) is int
    forward = canonical_implementation.request_fingerprint({"items": ("a", "b")})
    reverse = canonical_implementation.request_fingerprint({"items": ("b", "a")})
    assert forward != reverse
    assert canonical_implementation.canonical_value(("a", "b")) == ["a", "b"]
    assert canonical_implementation.canonical_value(["a", "b"]) == ["a", "b"]


def test_authority_object_safety() -> None:
    first = EditorGenerationExecutionRequestAuthorityV1()
    second = EditorGenerationExecutionRequestAuthorityV1()
    assert not hasattr(first, "__dict__")
    assert repr(first) == "EditorGenerationExecutionRequestAuthorityV1()"
    assert first == second and first != object()
    assert copy.copy(first) is first
    assert copy.deepcopy(first) is first
    with pytest.raises(TypeError):
        pickle.dumps(first)


def test_failure_traceback_is_content_isolated(semantic_values) -> None:
    secret = "TRACEBACK_SECRET_4_2_AUTHORITY"
    values = list(semantic_values)
    values[10] = secret + " "
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        construct(tuple(values))
    traceback = caught.value.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename.replace("/", "\\")
        if (
            "\\src\\pastila_scout\\editor_generation_execution_request_authority_v1\\"
            in filename
        ):
            assert secret not in repr(traceback.tb_frame.f_locals)
        traceback = traceback.tb_next
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


def _assert_recursive_authority_isolation(error, protected) -> None:
    protected_ids = {id(value) for value in protected}
    seen = set()

    def inspect_value(value):
        if value is None or id(value) in seen:
            return
        seen.add(id(value))
        assert id(value) not in protected_ids
        if isinstance(value, BaseException):
            inspect_value(value.__context__)
            inspect_value(value.__cause__)
            traceback = value.__traceback__
            while traceback is not None:
                filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
                if (
                    "/src/pastila_scout/"
                    "editor_generation_execution_request_authority_v1/" in filename
                ):
                    inspect_value(traceback.tb_frame.f_locals)
                traceback = traceback.tb_next
        elif isinstance(value, dict):
            for key, nested in value.items():
                inspect_value(key)
                inspect_value(nested)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for nested in value:
                inspect_value(nested)

    inspect_value(error)
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


@pytest.mark.parametrize(
    ("index", "attribute"),
    [
        (0, "plan"),
        (1, "source_report_id"),
        (2, "output"),
        (3, "flow_order"),
        (4, "flow_order"),
        (5, "flow_order"),
        (6, "provider"),
        (7, "model_identifier"),
        (11, "cancellation_requested"),
    ],
)
def test_recursive_traceback_isolation_for_each_nested_reconstruction(
    semantic_values, index, attribute
) -> None:
    values = list(semantic_values)
    invalid = copy.copy(values[index])
    object.__setattr__(invalid, attribute, object())
    values[index] = invalid
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        construct(tuple(values))
    _assert_recursive_authority_isolation(caught.value, (*values, invalid))


@pytest.mark.parametrize(
    "boundary",
    (
        "configuration",
        "lineage",
        "canonicalization",
        "frozen_construction",
        "frozen_reconstruction",
        "semantic_parity",
        "internal_corruption",
    ),
)
def test_recursive_traceback_isolation_for_late_boundaries(
    monkeypatch, semantic_values, boundary
) -> None:
    values = list(semantic_values)
    if boundary == "configuration":
        values[8] = ProviderChoiceV1.OLLAMA
    elif boundary == "lineage":
        alternate = alternate_preparation()
        assert alternate.plan is not None
        values[1] = alternate.plan
    elif boundary == "canonicalization":
        monkeypatch.setattr(
            implementation,
            "request_projection",
            lambda values: (_ for _ in ()).throw(RuntimeError()),
        )
    elif boundary == "frozen_construction":
        monkeypatch.setattr(
            implementation,
            "_frozen_construct",
            lambda values, fingerprint: (_ for _ in ()).throw(RuntimeError()),
        )
    elif boundary == "frozen_reconstruction":
        original = implementation.copy.copy

        def fail(value):
            if type(value) is EditorGenerationExecutionRequestV1:
                raise RuntimeError
            return original(value)

        monkeypatch.setattr(implementation.copy, "copy", fail)
    elif boundary == "semantic_parity":
        monkeypatch.setattr(implementation, "_semantic_match", lambda *values: False)
    else:
        monkeypatch.setattr(implementation, "_construct", lambda values: (None, None))
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        construct(tuple(values))
    _assert_recursive_authority_isolation(caught.value, tuple(values))


@pytest.mark.parametrize(
    "boundary",
    (
        "canonicalization",
        "frozen_construction",
        "frozen_reconstruction",
        "semantic_parity",
        "internal_corruption",
    ),
)
def test_real_late_private_boundaries_fail_closed(
    monkeypatch, semantic_values, boundary
) -> None:
    if boundary == "canonicalization":
        monkeypatch.setattr(
            implementation,
            "request_projection",
            lambda values: (_ for _ in ()).throw(TypeError()),
        )
    elif boundary == "frozen_construction":
        monkeypatch.setattr(
            implementation,
            "_frozen_construct",
            lambda values, fingerprint: (_ for _ in ()).throw(TypeError()),
        )
    elif boundary == "frozen_reconstruction":
        original = implementation.copy.copy

        def fail_request_copy(value):
            if type(value) is EditorGenerationExecutionRequestV1:
                raise TypeError
            return original(value)

        monkeypatch.setattr(implementation.copy, "copy", fail_request_copy)
    elif boundary == "semantic_parity":
        monkeypatch.setattr(implementation, "_semantic_match", lambda *values: False)
    else:
        monkeypatch.setattr(implementation, "_construct", lambda values: (None, None))
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        construct(semantic_values)
    assert type(caught.value) is EditorGenerationExecutionRequestAuthorityError
    assert str(caught.value) == (
        "Editor generation execution request authority is invalid."
    )
    assert vars(caught.value) == {}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_invalid_retained_request_state_uses_real_extraction_boundary() -> None:
    request = object.__new__(EditorGenerationExecutionRequestV1)
    status, result = implementation._reconstruct(request)
    assert status is implementation._Status.INVALID_REQUEST_STATE
    assert result is None
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    _assert_recursive_authority_isolation(caught.value, (request,))


def test_exact_input_failure_has_recursive_traceback_isolation() -> None:
    protected = object()
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=protected)
    _assert_recursive_authority_isolation(caught.value, (protected,))


@pytest.mark.parametrize(
    ("index", "attribute", "expected"),
    [
        (0, "plan", implementation._Status.INVALID_PREPARATION),
        (1, "source_report_id", implementation._Status.INVALID_GENERATION_PLAN),
        (2, "output", implementation._Status.INVALID_FLOW_RESULT),
        (3, "flow_order", implementation._Status.INVALID_EDITORIAL_BLUEPRINT),
        (4, "flow_order", implementation._Status.INVALID_COMMENTARY_BLUEPRINT),
        (5, "flow_order", implementation._Status.INVALID_VOICE_PLAN),
        (6, "provider", implementation._Status.INVALID_GENERATION_CONFIGURATION),
        (7, "model_identifier", implementation._Status.INVALID_RUNTIME_OPTIONS),
        (11, "cancellation_requested", implementation._Status.INVALID_CANCELLATION),
    ],
)
def test_reconstruct_reaches_each_real_nested_boundary(
    monkeypatch, semantic_values, index, attribute, expected
) -> None:
    values = list(semantic_values)
    invalid = copy.copy(values[index])
    object.__setattr__(invalid, attribute, object())
    values[index] = invalid
    canonical_calls = 0

    def projection(values):
        nonlocal canonical_calls
        del values
        canonical_calls += 1

    monkeypatch.setattr(implementation, "request_projection", projection)
    request = invalid_request(tuple(values))
    status, result = implementation._reconstruct(request)
    assert status is expected
    assert result is None
    assert canonical_calls == 0
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    _assert_recursive_authority_isolation(caught.value, (*values, request))


@pytest.mark.parametrize(
    ("index", "replacement", "expected"),
    [
        (8, object(), implementation._Status.INVALID_PROVIDER),
        (
            9,
            datetime(2026, 8, 5, 12),  # noqa: DTZ001 - intentional invalid input
            implementation._Status.INVALID_REQUESTED_TIMESTAMP,
        ),
        (10, " invalid ", implementation._Status.INVALID_REQUEST_REFERENCE),
    ],
)
def test_reconstruct_reaches_scalar_validation_boundaries(
    semantic_values, index, replacement, expected
) -> None:
    values = list(semantic_values)
    values[index] = replacement
    request = invalid_request(tuple(values))
    status, result = implementation._reconstruct(request)
    assert status is expected
    assert result is None
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError) as caught:
        EditorGenerationExecutionRequestAuthorityV1().reconstruct(request=request)
    _assert_recursive_authority_isolation(caught.value, (*values, request))


def test_canonical_failure_prevents_frozen_construction(
    monkeypatch, semantic_values
) -> None:
    calls = 0

    def fail(values):
        del values
        raise TypeError

    def frozen(values, fingerprint):
        nonlocal calls
        del values, fingerprint
        calls += 1

    monkeypatch.setattr(implementation, "request_projection", fail)
    monkeypatch.setattr(implementation, "_frozen_construct", frozen)
    with pytest.raises(EditorGenerationExecutionRequestAuthorityError):
        construct(semantic_values)
    assert calls == 0


def test_import_is_passive_in_fresh_process() -> None:
    script = "import pastila_scout.editor_generation_execution_request_authority_v1"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_cross_process_request_determinism() -> None:
    root = Path(__file__).resolve().parents[1]
    script = """
import json
import runpy
namespace = runpy.run_path('tests/test_editor_generation_execution_request_authority_v1.py')
values = namespace['semantic_values'].__wrapped__()
request = namespace['construct'](values)
print(json.dumps({
    'fingerprint': request.request_fingerprint,
    'provider': request.provider.value,
    'reference': request.request_reference,
    'requested_at': request.requested_at.isoformat(),
    'repr': repr(request),
}, sort_keys=True))
"""
    outputs = []
    for seed in ("1", "987654"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0
        assert completed.stderr == ""
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]


def test_private_import_and_aggregate_duplication_audit() -> None:
    root = Path(__file__).resolve().parents[1]
    package = (
        root
        / "src"
        / "pastila_scout"
        / "editor_generation_execution_request_authority_v1"
    )
    production = tuple(sorted(package.glob("*.py")))
    assert tuple(path.name for path in production) == (
        "__init__.py",
        "authority.py",
        "canonical.py",
        "errors.py",
    )
    sha_owners = []
    projection_owners = []
    for path in production:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("pastila_scout")
            ):
                assert not any(alias.name.startswith("_") for alias in node.names)
                assert not any(part.startswith("_") for part in node.module.split("."))
            if isinstance(node, ast.Import):
                assert not any(
                    part.startswith("_")
                    for alias in node.names
                    if alias.name.startswith("pastila_scout")
                    for part in alias.name.split(".")
                )
        if "sha256(" in source:
            sha_owners.append(path.name)
        if "def request_projection(" in source:
            projection_owners.append(path.name)
    assert sha_owners == ["canonical.py"]
    assert projection_owners == ["canonical.py"]
    focused_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "request_projection"
        for node in ast.walk(focused_tree)
    )
    protected = (
        root
        / "docs"
        / "editorial-application"
        / "EditorApplicationCompositionSpecificationV1.md"
    ).read_text(encoding="utf-8")
    assert "def request_projection(" not in protected


def test_current_revision_git_scope_and_frozen_integrity_are_exact() -> None:
    """Verify the frozen authority without claiming future repository state."""
    root = Path(__file__).resolve().parents[1]
    baseline = "phase-4.2-editor-generation-execution-request-authority-r2-verified"
    production_paths = (
        "src/pastila_scout/editor_generation_execution_request_authority_v1/__init__.py",
        "src/pastila_scout/editor_generation_execution_request_authority_v1/authority.py",
        "src/pastila_scout/editor_generation_execution_request_authority_v1/canonical.py",
        "src/pastila_scout/editor_generation_execution_request_authority_v1/errors.py",
    )
    test_path = "tests/test_editor_generation_execution_request_authority_v1.py"
    frozen_paths = (*production_paths, test_path)
    correction_digest = (
        "9536835DF76C973B5890AB3466318FA2227989BE2E666577AEAACDF7189A99DB"
    )

    def names(*arguments):
        return set(
            subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )

    resolved_baseline = subprocess.run(
        ["git", "rev-parse", f"{baseline}^{{}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert resolved_baseline == "3a6dab653510a0251f0d63a5a10fb2a5ff8d8838"
    assert names("ls-files", "--error-unmatch", *frozen_paths) == set(frozen_paths)
    assert all((root / path).is_file() for path in frozen_paths)
    assert names("diff", "--name-only", baseline, "--", *production_paths) == set()
    assert names("diff", "--cached", "--name-only", "--", *frozen_paths) == set()
    assert not set(frozen_paths).intersection(
        names("ls-files", "--others", "--exclude-standard")
    )
    assert names("diff", "--name-only", "--", *frozen_paths) == {test_path}

    test_bytes = (root / test_path).read_bytes()
    normalized = test_bytes.replace(correction_digest.encode(), b"0" * 64)
    assert normalized != test_bytes
    assert hashlib.sha256(normalized).hexdigest().upper() == correction_digest


def test_caller_fingerprint_is_impossible() -> None:
    signature = inspect.signature(EditorGenerationExecutionRequestAuthorityV1.construct)
    prohibited = {
        "request_fingerprint",
        "digest",
        "payload",
        "callback",
        "override",
    }
    assert prohibited.isdisjoint(signature.parameters)
    assert all(
        item.kind
        not in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}
        for item in signature.parameters.values()
    )
