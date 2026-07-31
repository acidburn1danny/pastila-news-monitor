"""Opt-in, one-request OpenAI Controlled Revision production smoke test."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

import openai
from pydantic import SecretStr

from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.config import load_application_config
from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderConfiguration,
    AIProviderExecutionObserver,
    AIProviderExecutionStatus,
    AIProviderObservabilityEventCode,
    AIRetryPolicy,
    AIStructuredOutputCapabilities,
    AIStructuredOutputMode,
    build_ai_provider_execution_safe_report,
    serialize_ai_provider_execution_safe_report,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionAdapter,
    compose_openai_controlled_revision_adapter,
)
from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.generation.revision import (
    ControlledRevisionInstructions,
    ControlledRevisionInvocation,
    ControlledRevisionOutputContract,
    ControlledRevisionPolicy,
    ControlledRevisionRequest,
    ControlledRevisionTarget,
    DraftPreservationRequirements,
    RevisionTargetType,
    revision_fingerprint,
    validate_revision_gateway_result,
)

OPT_IN = "SCOUT_RUN_LIVE_OPENAI_TESTS"
FP_A = "sha256:" + "a" * 64
FP_B = "sha256:" + "b" * 64
SOURCE = (
    "Primăria orașului Lumen a deschis luni un parc mic în cartierul de nord. "
    "Parcul are douăzeci de copaci, opt bănci și un loc de joacă. "
    "Evenimentul a început la ora zece."
)
INSTRUCTION = (
    "Corectează formularea pentru claritate și fluență, fără să adaugi fapte noi "
    "și fără să schimbi cifrele sau ora."
)
REQUIRED_FACTS = (
    "orașului Lumen",
    "luni",
    "douăzeci de copaci",
    "opt bănci",
    "un loc de joacă",
    "ora zece",
)


class EnvironmentCredentialProvider:
    """Resolve the approved external OpenAI credential without retaining it."""

    def __init__(self) -> None:
        self.resolution_count = 0

    def resolve(self, authentication_reference: str) -> SecretStr:
        self.resolution_count += 1
        if authentication_reference != "env:OPENAI_API_KEY":
            raise ValueError("unsupported credential reference")
        value = resolve_openai_api_key()
        if not value:
            raise ValueError("approved OpenAI credential is unavailable")
        return SecretStr(value)


class CountingOpenAIFactory:
    """Count SDK construction while delegating unchanged to the official client."""

    def __init__(self) -> None:
        self.construction_count = 0

    def __call__(self, **values: Any) -> openai.OpenAI:
        self.construction_count += 1
        return openai.OpenAI(**values)


class EventRecorder(AIProviderExecutionObserver):
    """Collect the canonical content-free runtime events."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


@dataclass
class CapturingRuntime:
    """Expose the canonical result while retaining the production gateway boundary."""

    runtime: Any
    result: Any = None

    def execute(self, invocation: ControlledRevisionInvocation) -> Any:
        self.result = self.runtime.execute(invocation)
        return self.result


def build_invocation() -> ControlledRevisionInvocation:
    """Build the synthetic request exclusively through frozen domain factories."""

    closing = "Sfârșit."
    source = EpisodeDraft(
        episode_id="smoke-openai-controlled-revision",
        opening=SOURCE,
        stories=(),
        transitions=(),
        closing=closing,
        cta=None,
        assembled_text=f"{SOURCE}\n\n{closing}",
        teleprompter_text=f"{SOURCE}\n\n{closing}",
    )
    target = ControlledRevisionTarget.build(
        target_type=RevisionTargetType.OPENING,
        upstream_target_fingerprint=FP_A,
    )
    policy = ControlledRevisionPolicy.build(
        maximum_revision_targets=1,
        upstream_policy_fingerprint=FP_A,
    )
    instructions = ControlledRevisionInstructions.build(
        editorial_instruction=INSTRUCTION,
        authorized_scope_fingerprint=FP_A,
        upstream_instructions_fingerprint=FP_B,
    )
    source_fingerprint = revision_fingerprint(source)
    preservation = DraftPreservationRequirements.build(
        source_draft_fingerprint=source_fingerprint,
        allowed_target_fingerprints=(target.target_fingerprint,),
        protected_component_fingerprints=(("closing", revision_fingerprint(closing)),),
        upstream_scope_fingerprint=FP_A,
    )
    output = ControlledRevisionOutputContract.build(
        source_draft_fingerprint=source_fingerprint,
        preservation_fingerprint=preservation.preservation_fingerprint,
    )
    request = ControlledRevisionRequest.build(
        source_draft=source,
        revision_targets=(target,),
        revision_instructions=instructions,
        revision_policy=policy,
        preservation_requirements=preservation,
        expected_output_contract=output,
        planning_input_fingerprint=FP_A,
        executor_request_fingerprint=FP_B,
    )
    return ControlledRevisionInvocation.build(request=request)


def configuration(model: str) -> AIProviderConfiguration:
    """Create an execution-local, single-attempt bounded configuration."""

    return AIProviderConfiguration(
        provider_identifier="openai",
        model_identifier=model,
        authentication_reference="env:OPENAI_API_KEY",
        timeout_seconds=30,
        retry_policy=AIRetryPolicy(maximum_attempts=1),
        structured_output=AIStructuredOutputCapabilities(
            supported_modes=(
                AIStructuredOutputMode.JSON,
                AIStructuredOutputMode.SCHEMA_CONSTRAINED,
            )
        ),
        maximum_context_tokens=32_000,
    )


def print_preflight(model: str, credential_available: bool) -> None:
    """Print only non-sensitive request characteristics."""

    print("Controlled OpenAI Live Smoke Test — Preflight")
    print("Provider: openai")
    print(f"Requested model: {model}")
    print("Timeout: 30 seconds")
    print("Max attempts: 1")
    print(f"Source character count: {len(SOURCE)}")
    print(f"Instruction character count: {len(INSTRUCTION)}")
    print("Schema name: controlled_revision_patch_v1")
    print("Live-request budget: 1")
    print(f"Credential available: {'YES' if credential_available else 'NO'}")


def _event_count(events: list[Any], code: AIProviderObservabilityEventCode) -> int:
    return sum(event.code is code for event in events)


def _safe_reporting(result: Any, events: list[Any], revised_text: str) -> bool:
    report = serialize_ai_provider_execution_safe_report(
        build_ai_provider_execution_safe_report(result)
    )
    event_text = "\n".join(event.model_dump_json() for event in events)
    observable = report + event_text
    forbidden = (SOURCE, revised_text, INSTRUCTION, *REQUIRED_FACTS)
    return not any(value and value in observable for value in forbidden)


def _unsupported_fact_check(text: str) -> bool:
    """Apply narrow deterministic checks suitable for the synthetic fixture."""

    if re.search(r"\d", text):
        return False
    protected_names = set(re.findall(r"\b[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț-]+", text))
    return protected_names <= {"Lumen", "Primăria", "Parcul", "Evenimentul"}


def main() -> int:
    """Run a safe dry preflight or exactly one live semantic execution."""

    app = load_application_config(Path("config/config.yaml"))
    model = app.ai.model
    credential_available = resolve_openai_api_key() is not None
    invocation = build_invocation()
    original_fingerprint = invocation.invocation_fingerprint
    print_preflight(model, credential_available)
    if not credential_available:
        print("Status: STOPPED — approved credential unavailable")
        return 2
    if os.environ.get(OPT_IN) != "1":
        print(f"Status: SKIPPED — set {OPT_IN}=1 for the one-request live test")
        return 0

    credentials = EnvironmentCredentialProvider()
    sdk_factory = CountingOpenAIFactory()
    observer = EventRecorder()
    composition = compose_openai_controlled_revision_adapter(
        configuration=configuration(model),
        credential_provider=credentials,
        client_factory=sdk_factory,
        execution_observer=observer,
    )
    capture = CapturingRuntime(composition.runtime_composition.runtime)
    gateway = OpenAIControlledRevisionAdapter(composition.configuration, capture)
    started = monotonic()
    try:
        gateway_result = gateway.revise(invocation)
    except Exception:  # noqa: BLE001 - the live boundary must suppress unsafe details
        result = capture.result
        code = (
            result.diagnostic.diagnostic_code
            if result is not None and result.diagnostic is not None
            else "unknown_failure"
        )
        print("Status: FAIL")
        print(f"Safe diagnostic: {code}")
        return 1
    elapsed_ms = (monotonic() - started) * 1000
    result = capture.result
    validate_revision_gateway_result(gateway_result, invocation)
    revised = gateway_result.revised_draft
    revised_text = revised.opening
    distinct = revised != invocation.request.source_draft
    preserved = all(
        value.casefold() in revised_text.casefold() for value in REQUIRED_FACTS
    )
    structural = (
        revised.episode_id == invocation.request.source_draft.episode_id
        and revised.closing == invocation.request.source_draft.closing
        and revised.stories == invocation.request.source_draft.stories
        and revised.transitions == invocation.request.source_draft.transitions
    )
    safe = _safe_reporting(result, observer.events, revised_text)
    checks = (
        result.status is AIProviderExecutionStatus.SUCCESS,
        invocation.invocation_fingerprint == original_fingerprint,
        distinct,
        preserved,
        structural,
        _unsupported_fact_check(revised_text),
        safe,
        len(result.attempts) == 1,
        credentials.resolution_count == 1,
        sdk_factory.construction_count == 1,
        _event_count(
            observer.events, AIProviderObservabilityEventCode.PROJECTION_COMPLETED
        )
        == 1,
        _event_count(
            observer.events, AIProviderObservabilityEventCode.INTERPRETATION_COMPLETED
        )
        == 1,
    )
    if not all(checks):
        print("Status: FAIL")
        print("Safe diagnostic: smoke_test_invariant_failed")
        return 1

    interpretation = result.interpretation_result
    usage = result.usage
    print("Status: PASS")
    print("Provider: openai")
    print(f"Requested model: {model}")
    print(
        "Returned model available: "
        f"{'YES' if interpretation.provider_model_identifier else 'NO'}"
    )
    print("Runtime attempts: 1")
    print("SDK calls: 1")
    print("Gateway result: valid")
    print("Distinct draft: yes")
    print("Romanian language preservation: pass")
    print("Preservation validation: pass")
    print("Unsupported-fact check: pass")
    print("Lineage validation: pass")
    print(f"Usage available: {'YES' if usage.total_tokens >= 0 else 'NO'}")
    print(
        "Provider request ID available: "
        f"{'YES' if interpretation.provider_request_identifier else 'NO'}"
    )
    print(f"Input tokens: {usage.prompt_tokens}")
    print(f"Output tokens: {usage.completion_tokens}")
    print(f"Total tokens: {usage.total_tokens}")
    print(f"Duration milliseconds: {elapsed_ms:.0f}")
    print("Safe reporting: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
