"""Offline verification for the application provider-request authority."""

from __future__ import annotations

import copy
import json
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.application_request_authority_v1 as public_api
from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityError,
    ApplicationRequestAuthorityV1,
    canonical,
)
from pastila_scout.application_request_authority_v1.models import (
    MAX_PROMPT_CHARACTERS,
)
from pastila_scout.provider_adapters_v2.ollama import OllamaProviderAdapter
from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 6, 12, 30, tzinfo=UTC)
PROMPT = "Preserve this exact application prompt."


def _application_request(
    provider: ProviderChoiceV1 = ProviderChoiceV1.OPENAI,
    **changes,
) -> ApplicationProviderRequestV1:
    values = {
        "provider": provider,
        "prompt": PROMPT,
        "request_reference": "controlled-application-request-1",
        "requested_at": NOW,
        "timeout_policy": TimeoutPolicyV2(timeout_seconds=17),
        "cancellation": CancellationTokenV2(cancellation_requested=False),
    }
    values.update(changes)
    return ApplicationProviderRequestV1(**values)


def test_public_api_is_exact_and_ordered() -> None:
    assert public_api.__all__ == (
        "ApplicationProviderRequestV1",
        "ApplicationRequestAuthorityError",
        "ApplicationRequestAuthorityV1",
    )


@pytest.mark.parametrize(
    ("choice", "descriptor"),
    (
        (ProviderChoiceV1.OPENAI, OpenAIProviderAdapter.descriptor),
        (ProviderChoiceV1.OLLAMA, OllamaProviderAdapter.descriptor),
    ),
)
def test_builds_exact_provider_authority_with_one_prompt_unit(
    choice, descriptor
) -> None:
    source = _application_request(choice)

    result = ApplicationRequestAuthorityV1().build(source)

    assert type(result) is ProviderExecutionRequestV2
    assert result.provider == descriptor
    assert result.provider.identity == descriptor.identity
    assert result.provider.fingerprint == descriptor.fingerprint
    assert len(result.request_intent.request_units) == 1
    assert len(result.request_envelope.request_units) == 1
    intent_unit = result.request_intent.request_units[0]
    envelope_unit = result.request_envelope.request_units[0]
    assert intent_unit.ordinal == envelope_unit.ordinal == 0
    assert len(intent_unit.messages) == len(envelope_unit.messages) == 1
    assert (
        intent_unit.messages[0].role == envelope_unit.messages[0].role == "generation"
    )
    assert (
        intent_unit.messages[0].content == envelope_unit.messages[0].content == PROMPT
    )
    assert (
        intent_unit.source_request_reference == envelope_unit.source_request_reference
    )


def test_timeout_cancellation_context_and_empty_metadata_are_preserved() -> None:
    source = _application_request(
        timeout_policy=TimeoutPolicyV2(timeout_seconds=3.5),
        cancellation=CancellationTokenV2(cancellation_requested=True),
    )

    result = ApplicationRequestAuthorityV1().build(source)

    assert result.context.requested_at == NOW
    assert result.context.cancellation.cancellation_requested is True
    assert result.context.metadata == ()
    assert result.timeout_policy.timeout_seconds == 3.5


def test_provider_neutral_intent_is_identical_across_provider_choices() -> None:
    authority = ApplicationRequestAuthorityV1()
    openai = authority.build(_application_request(ProviderChoiceV1.OPENAI))
    ollama = authority.build(_application_request(ProviderChoiceV1.OLLAMA))

    assert openai.request_intent == ollama.request_intent
    assert openai.context == ollama.context
    assert openai.timeout_policy == ollama.timeout_policy
    assert (
        openai.request_envelope.descriptor_identity
        != ollama.request_envelope.descriptor_identity
    )


@pytest.mark.parametrize("choice", (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA))
def test_composed_and_decomposed_prompts_have_identical_lower_authority(choice) -> None:
    composed = "Răspunde exact: OK"
    decomposed = "Ra\u0306spunde exact: OK"
    composed_source = _application_request(choice, prompt=composed)
    decomposed_source = _application_request(choice, prompt=decomposed)

    composed_result = ApplicationRequestAuthorityV1().build(composed_source)
    decomposed_result = ApplicationRequestAuthorityV1().build(decomposed_source)

    assert composed_source.prompt == composed
    assert decomposed_source.prompt == decomposed
    assert composed_source.prompt != decomposed_source.prompt
    assert composed_result == decomposed_result
    assert (
        decomposed_result.request_intent.request_units[0].messages[0].content
        == composed
    )
    assert (
        decomposed_result.request_envelope.request_units[0].messages[0].content
        == composed
    )


def test_nfc_is_applied_once_by_application_authority(monkeypatch) -> None:
    calls = []
    unicode_module = canonical.unicodedata

    class UnicodeProxy:
        @staticmethod
        def normalize(form, value):
            calls.append((form, value))
            return unicode_module.normalize(form, value)

    monkeypatch.setattr(canonical, "unicodedata", UnicodeProxy)
    prompt = "Ra\u0306spunde"

    ApplicationRequestAuthorityV1().build(_application_request(prompt=prompt))

    assert calls == [("NFC", prompt)]


def test_canonicalization_does_not_apply_nfkc_or_change_internal_whitespace() -> None:
    fullwidth = ApplicationRequestAuthorityV1().build(
        _application_request(prompt="Ａ  B\tC")
    )
    ascii_text = ApplicationRequestAuthorityV1().build(
        _application_request(prompt="A  B\tC")
    )

    actual = fullwidth.request_intent.request_units[0].messages[0].content
    assert actual == "Ａ  B\tC"
    assert actual != ascii_text.request_intent.request_units[0].messages[0].content
    assert fullwidth.request_intent != ascii_text.request_intent


def test_forged_noncanonical_lower_reconstruction_fails_closed(monkeypatch) -> None:
    original = ProviderExecutionRequestV2.model_validate

    def forge(cls, value, *, strict=None, **kwargs):
        rebuilt = original(value, strict=strict, **kwargs)
        intent = rebuilt.request_intent
        unit = intent.request_units[0]
        message = unit.messages[0].model_copy(update={"content": "a\u0306"})
        forged_unit = unit.model_copy(update={"messages": (message,)})
        forged_intent = intent.model_copy(update={"request_units": (forged_unit,)})
        return rebuilt.model_copy(update={"request_intent": forged_intent})

    monkeypatch.setattr(
        ProviderExecutionRequestV2, "model_validate", classmethod(forge)
    )

    with pytest.raises(
        ApplicationRequestAuthorityError,
        match="application provider request construction failed",
    ):
        ApplicationRequestAuthorityV1().build(_application_request(prompt="ă"))


def test_repeated_construction_has_stable_complete_lineage() -> None:
    source = _application_request(ProviderChoiceV1.OLLAMA)
    authority = ApplicationRequestAuthorityV1()

    first = authority.build(source)
    second = authority.build(source)

    assert first == second
    assert first.context.request_id == second.context.request_id
    assert (
        first.request_intent.execution_plan_identity
        == second.request_intent.execution_plan_identity
    )
    assert (
        first.request_intent.execution_plan_fingerprint
        == second.request_intent.execution_plan_fingerprint
    )
    assert first.request_envelope.identity == second.request_envelope.identity
    assert first.request_envelope.fingerprint == second.request_envelope.fingerprint
    assert (
        first.request_envelope.request_units[0].identity
        == second.request_envelope.request_units[0].identity
    )
    assert (
        first.request_envelope.request_units[0].fingerprint
        == second.request_envelope.request_units[0].fingerprint
    )


def test_cross_process_determinism() -> None:
    script = """
import json
from datetime import UTC, datetime
from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
r=ApplicationRequestAuthorityV1().build(ApplicationProviderRequestV1(ProviderChoiceV1.OPENAI,'Preserve this exact application prompt.','controlled-application-request-1',datetime(2026,8,6,12,30,tzinfo=UTC),TimeoutPolicyV2(timeout_seconds=17),CancellationTokenV2(cancellation_requested=False)))
print(json.dumps({'request_id':r.context.request_id,'plan':r.request_intent.execution_plan_identity,'plan_fingerprint':r.request_intent.execution_plan_fingerprint,'envelope':r.request_envelope.identity,'unit':r.request_envelope.request_units[0].identity},sort_keys=True))
"""
    outputs = tuple(
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        for _ in range(2)
    )
    assert outputs[0] == outputs[1]
    assert json.loads(outputs[0])["request_id"].startswith("application-request-v1:")


def test_isolated_ollama_authority_import_does_not_load_editor_cycle() -> None:
    script = """
from datetime import UTC, datetime
from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
r=ApplicationRequestAuthorityV1().build(ApplicationProviderRequestV1(ProviderChoiceV1.OLLAMA,'bounded voice prompt','voice-governed-realization:test',datetime(2026,8,25,18,0,tzinfo=UTC),TimeoutPolicyV2(timeout_seconds=120),CancellationTokenV2(cancellation_requested=False)))
print(r.provider.provider_id)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.stdout.strip() == "ollama"


@pytest.mark.parametrize(
    "provider",
    ("openai", "ollama", "OPENAI", "OLLAMA", "auto", None, object()),
)
def test_invalid_provider_values_and_aliases_are_rejected(provider) -> None:
    with pytest.raises(
        ApplicationRequestAuthorityError, match="invalid application provider request"
    ):
        _application_request(provider)  # type: ignore[arg-type]


class _PromptSubclass(str):
    pass


@pytest.mark.parametrize(
    "prompt",
    ("", " ", " padded", "padded ", _PromptSubclass("prompt")),
)
def test_invalid_blank_padded_and_subclassed_prompts_are_rejected(prompt) -> None:
    with pytest.raises(
        ApplicationRequestAuthorityError, match="invalid application provider request"
    ):
        _application_request(prompt=prompt)


def test_oversized_prompt_is_rejected_without_content_leak() -> None:
    prompt = "sensitive" * (MAX_PROMPT_CHARACTERS // 9 + 1)
    with pytest.raises(ApplicationRequestAuthorityError) as captured:
        _application_request(prompt=prompt)
    assert "sensitive" not in str(captured.value)


def test_valid_copy_deepcopy_pickle_and_safe_repr() -> None:
    source = _application_request()
    values = (
        copy.copy(source),
        copy.deepcopy(source),
        pickle.loads(pickle.dumps(source)),
    )
    assert all(value == source for value in values)
    rendered = repr(source)
    assert PROMPT not in rendered
    assert "redacted" in rendered
    assert not hasattr(source, "__dict__")


def test_copied_invalid_and_coordinated_substitution_fail_closed() -> None:
    source = _application_request()
    object.__setattr__(source, "prompt", "Different valid prompt")
    object.__setattr__(source, "request_reference", "different-valid-reference")

    for operation in (
        lambda: copy.copy(source),
        lambda: copy.deepcopy(source),
        lambda: pickle.dumps(source),
        lambda: ApplicationRequestAuthorityV1().build(source),
    ):
        with pytest.raises(ApplicationRequestAuthorityError):
            operation()


def test_copied_invalid_final_request_is_rejected_by_frozen_reconstruction() -> None:
    result = ApplicationRequestAuthorityV1().build(_application_request())
    corrupted = result.model_copy(
        update={
            "request_envelope": result.request_envelope.model_copy(
                update={"request_units": ()}
            )
        }
    )
    with pytest.raises(ValidationError):
        ProviderExecutionRequestV2.model_validate(
            corrupted.model_dump(mode="python", warnings=False), strict=True
        )


def test_public_objects_are_immutable_and_authority_has_safe_policy() -> None:
    source = _application_request()
    authority = ApplicationRequestAuthorityV1()
    with pytest.raises(FrozenInstanceError):
        source.prompt = "replacement"  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        source.extra = "value"  # type: ignore[attr-defined]
    assert copy.copy(authority) is copy.deepcopy(authority) is authority
    assert repr(authority) == "ApplicationRequestAuthorityV1()"
    assert not hasattr(authority, "__dict__")
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(authority)


def test_error_is_safe_and_isolated_for_invalid_retained_state() -> None:
    source = _application_request()
    object.__setattr__(source, "timeout_policy", object())
    with pytest.raises(ApplicationRequestAuthorityError) as captured:
        ApplicationRequestAuthorityV1().build(source)
    assert str(captured.value) == "application provider request construction failed"
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert PROMPT not in str(captured.value)


def test_import_is_passive_and_provider_implementations_do_not_load() -> None:
    script = """
import sys
import pastila_scout.application_request_authority_v1
for forbidden in ('openai','pastila_scout.provider_execution_openai_v2','pastila_scout.provider_execution_ollama_v1'):
    assert forbidden not in sys.modules, forbidden
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
    assert completed.stdout == completed.stderr == ""
