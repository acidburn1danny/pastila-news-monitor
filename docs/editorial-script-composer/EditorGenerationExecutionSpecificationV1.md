# Phase 4.2 — Editor Generation Execution Specification V3

Status: **normative specification — strict JSON-mode and runtime-session boundaries corrected**

Baseline: `phase-4.2-editor-generation-provider-r3c-verified` / `0afbe27480623e1f100b5275109b46ac3572bc3a`

## 1. Normative scope

The words **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, and **MAY** are
normative. This document specifies additive future work only. It changes no
frozen contract or implementation.

The future coordinator flow is exactly:

```text
EditorOperationalPreparationResultV1
  -> EditorGenerationPreparationCoordinatorV1
  -> EditorGenerationExecutionRequestV1
  -> EditorOperationalExecutionCoordinatorV1
  -> ControlledGenerator
  -> EditorNeutralLanguageModelProviderV1
  -> EditorGenerationApplicationRequestV1
  -> EditorGenerationRequestAuthorityV1
  -> ScoutWorkflowExecutionV1.execute_provider_neutral
  -> ScoutRuntimeExecutionBridgeV1
  -> ProviderSelectorV1
  -> selected verified executor
  -> strict JSON/output_schema validation
  -> ControlledGenerationResult
  -> EditorOperationalResultV1
```

`EditorOperationalCoordinatorV1` and `EditorGenerationPlanV1` remain unchanged.
There is no CLI, persistence, Producer handoff, fallback, automatic routing, or
direct provider execution.

The Revision 3C adapter flow begins at `ControlledGenerator` and does not
include either `EditorGenerationExecutionRequestV1` or any deterministic Editor
artifact. The execution request belongs exclusively to the coordinator prefix
of the flow above.

## 2. Reproduced blockers and repository grounding

### 2.1 Option transport

`LanguageGenerationConfig` contains `provider`, `model_identifier`,
`model_revision`, `temperature`, `top_p`, `max_output_tokens`, `seed`,
`structured_output_mode`, and `timeout_seconds`.

`ProviderExecutionRequestV2` contains provider descriptor, request intent,
request envelope, context/cancellation snapshot, and timeout policy. Neither it
nor `ProviderRequestIntentV2` has generation-option or schema fields.

The verified OpenAI and Ollama executors instead receive temperature, maximum
output tokens, and stop sequences in their immutable executor configurations.
OpenAI accepts temperature and maximum output tokens; its Responses bridge
fails closed for nonempty stops. Ollama maps temperature, maximum output tokens,
and stops. Neither verified executor exposes top-p, seed, or native structured
schema configuration.

Therefore options MUST be bound at application composition to one immutable
runtime session and cryptographically included in application request identity.
They MUST NOT be fabricated as lower request fields.

### 2.2 Missing deterministic artifacts

`ControlledGenerator.generate` requires Scout input, selection profile, episode
context, flow result, editorial blueprint, commentary blueprint, and voice plan.
The frozen Revision 2 plan intentionally contains only selection preparation.

Existing deterministic sources are complete:

| Artifact | Existing constructor | Exact source |
|---|---|---|
| selection result | `EditorialSelectionResult(output, trace)` | frozen plan output/trace |
| flow result | `EpisodeFlowOptimizer.optimize` | source/profile/context/selection result |
| editorial blueprint | `EditorialBlueprintBuilder.build(...).blueprint` | flow result |
| commentary blueprint | `CommentaryBlueprintBuilder.build(...).blueprint` | flow and editorial blueprint |
| voice plan | `VoiceModelBuilder.build(...).plan` | flow, editorial, commentary |

No new AI authority or invented artifact is required.

### 2.3 Frozen coordinator and missing result

Revision 2 preparation remains separate. A new execution coordinator is
required. `EditorOperationalResultV1` is specified in section 12.

## 3. Exact package and dependency roadmap

Future implementation SHALL use five additive packages:

```text
src/pastila_scout/editor_generation_authority_v1/
    __init__.py
    authority.py
    errors.py
    models.py

src/pastila_scout/editor_generation_execution_v1/
    __init__.py
    enrichment.py
    errors.py
    models.py
    protocols.py

src/pastila_scout/editor_generation_provider_adapter_v1/
    __init__.py
    adapter.py
    application_request.py
    errors.py
    parsing.py
    protocols.py

src/pastila_scout/editor_generation_runtime_v1/
    __init__.py
    composition.py
    errors.py
    models.py
    protocols.py

src/pastila_scout/editor_operational_execution_v1/
    __init__.py
    coordinator.py
    errors.py
    models.py
    protocols.py
```

Dependency direction is strictly:

```text
editor_operational_execution_v1
  -> editor_generation_execution_v1
  -> editor_generation_runtime_v1
  -> editor_generation_provider_adapter_v1
  -> editor_generation_authority_v1
  -> frozen public application/workflow/runtime contracts

editor_generation_execution_v1
  -> frozen Revision 2 public API and existing deterministic Editor API

editor_generation_provider_adapter_v1
  -> existing LanguageModelProvider/GenerationPrompt
  -> editor_generation_authority_v1
  -> frozen Scout workflow API

editor_generation_runtime_v1
  -> verified public OpenAI/Ollama composition and Scout workflow APIs
```

The authority package imports no Editor domain type. The adapter imports no
provider implementation, SDK, deterministic builder, coordinator, CLI,
persistence, or Producer type. Frozen packages never import these packages.
The adapter MUST NOT import `editor_generation_execution_v1` or
`editor_operational_v1`.

## 4. Generation-capable application authority

### 4.1 Representation classification

| Semantic field | Representation | Rule |
|---|---|---|
| provider choice | existing selector plus descriptor | exact `ProviderChoiceV1` |
| prompt | lower single `generation` message | exact authority-owned NFC canonicalization |
| temperature | bound runtime configuration | exact int/float, 0–2 |
| maximum output tokens | bound runtime configuration | exact positive int |
| timeout | `TimeoutPolicyV2` and bound runtime | values MUST be numerically identical |
| cancellation | `ExecutionContextV2.cancellation` | fresh snapshot per adapter call |
| top-p | not representable | only exact `1.0` accepted; all other values fail pre-composition |
| seed | not representable | only `None` accepted |
| stop sequences | not used by `ControlledGenerator` | must be exact empty tuple; nonempty fails |
| structured-output mode | application prompt plus strict parser/schema | must be exact `True` |
| model identifier/revision | bound runtime configuration | exact identifier; revision may be null but is identity-bound |
| output schema | prompt layer plus authority fingerprint | section 5 |

Exact `top_p == 1.0`, `seed is None`, empty stops, and structured mode true are
closed compatibility requirements, not silently dropped options. The authority
rejects other values before provider selection or execution.

### 4.2 `EditorGenerationRuntimeOptionsV1`

Fields, in order, all required and without defaults:

```python
provider: ProviderChoiceV1
model_identifier: str
model_revision: str | None
temperature: int | float
top_p: int | float
max_output_tokens: int
seed: None
stop_sequences: tuple[str, ...]
structured_output_mode: bool
timeout_policy: TimeoutPolicyV2
```

Exact types only; booleans are not numbers. Temperature is finite and within
0–2. Top-p MUST be numerically and type-stably reconstructed and equal `1` or
`1.0`; canonical form records its original exact numeric type and value. Model
identifier is unpadded nonempty NFC, at most 200 characters. Model revision is
null or the same string class. Maximum tokens is positive. Seed is exactly null,
stops exactly `()`, structured mode exact true. Timeout is strictly
reconstructed and equals the session timeout.

### 4.3 `EditorGenerationApplicationRequestV1`

Fields, in order:

```python
provider: ProviderChoiceV1
prompt: str
request_reference: str
requested_at: datetime
options: EditorGenerationRuntimeOptionsV1
output_schema_name: str
output_schema_canonical_json: str
output_schema_fingerprint: str
cancellation: CancellationTokenV2
request_fingerprint: str
```

All are required. Prompt is exact built-in, nonempty, unpadded, at most 200,000
characters. `requested_at` is aware. Schema name and request reference are
unpadded safe strings. Schema JSON must satisfy section 5. Fingerprints are
lowercase SHA-256. Provider MUST equal options provider.

The request fingerprint is SHA-256 over canonical UTF-8 JSON of every preceding
field except itself. Canonical JSON uses NFC strings, `ensure_ascii=False`,
sorted keys, separators `(",", ":")`, no nonfinite numbers, enums as values,
tuples as arrays, aware datetimes in UTC with six fractional digits and `Z`, and
numeric-type tags for temperature/top-p/timeout so integer and float authority
cannot collide.

### 4.4 `EditorGenerationRequestAuthorityV1`

Exact method:

```python
def build(
    self,
    request: EditorGenerationApplicationRequestV1,
    runtime_authority: EditorGenerationRuntimeAuthorityV1,
) -> ProviderExecutionRequestV2: ...
```

It is immutable, slotted, stateless, copy/deepcopy identity, address-free repr,
and rejects pickle. It reconstructs both inputs, requires exact provider,
model/options/timeout equality, and constructs exactly one lower request using
the same descriptor and envelope builders as the verified application
authority. Its semantic execution-plan fingerprint MUST bind the application
request fingerprint, including runtime options and schema fingerprint. It emits
one request unit and one `generation` message containing NFC(prompt). It creates
no client and performs no selection or execution.

### 4.5 `EditorGenerationRuntimeAuthorityV1`

Fields:

```python
options: EditorGenerationRuntimeOptionsV1
runtime_reference: str
runtime_fingerprint: str
```

The application composition root constructs this value atomically with the
selected verified runtime session. Its fingerprint covers the exact options and
runtime reference. The session composition MUST configure OpenAI/Ollama with
the exact model, temperature, max tokens, empty stops, and timeout. A declaration
not atomically produced with the session is invalid. This is the sole authority
connecting non-lower option values to the configured executor.

The runtime session factory is the sole construction owner and independently
reproduces the frozen V1 bytes without importing a private Revision 3B helper.
It reconstructs exact `EditorGenerationRuntimeOptionsV1`, then hashes exactly:

```python
{
    "options": {
        "provider": options.provider.value,
        "model_identifier": options.model_identifier,
        "model_revision": options.model_revision,
        "temperature": {
            "type": "int" if type(options.temperature) is int else "float",
            "value": options.temperature,
        },
        "top_p": {
            "type": "int" if type(options.top_p) is int else "float",
            "value": options.top_p,
        },
        "max_output_tokens": options.max_output_tokens,
        "seed": options.seed,
        "stop_sequences": options.stop_sequences,
        "structured_output_mode": options.structured_output_mode,
        "timeout_seconds": {
            "type": (
                "int"
                if type(options.timeout_policy.timeout_seconds) is int
                else "float"
            ),
            "value": options.timeout_policy.timeout_seconds,
        },
    },
    "runtime_reference": runtime_reference,
}
```

Every string value and key is normalized to NFC for fingerprint semantics;
tuples become ordered JSON arrays; nonfinite numbers and unsupported values are
rejected. Serialization is exactly
`json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
allow_nan=False)`. The runtime fingerprint is lowercase SHA-256 over those
UTF-8 bytes with no prefix. `runtime_reference` is exactly the already-validated
session operation reference; no second runtime/session identifier is invented.

The factory immediately constructs `EditorGenerationRuntimeAuthorityV1` with
the reconstructed options, exact reference, and digest, then reconstructs it
through public copy behavior and requires exact options/reference/digest parity.
Failure occurs before session publication and triggers normal partial cleanup.
The implementation MUST NOT import
`editor_generation_authority_v1.canonical`, `_options_semantics`,
`_option_values`, or any other private Revision 3B symbol. V1 deliberately
duplicates the frozen bytes because no public construction authority exists;
any future algorithm requires a new runtime-session version. Focused tests use
the frozen constructor as the parity oracle for integer/float tagged values,
Unicode, timeout types, provider/model, and operation reference.

### 4.6 Exact runtime-session composition

`EditorGenerationRuntimeSessionFactoryV1` has this exact constructor and method:

```python
def __init__(
    self,
    *,
    openai_composer_factory: EditorOpenAIRuntimeComposerFactoryV1,
    ollama_session_factory: EditorOllamaRuntimeFactoryV1,
    workflow_factory: EditorScoutWorkflowFactoryV1,
    adapter_dependency_factory: EditorAdapterDependencyFactoryV1,
    fingerprint_authority: EditorRequestFingerprintAuthorityV1,
) -> None: ...

def open(
    self,
    options: EditorGenerationRuntimeOptionsV1,
    *,
    operation_reference: str,
) -> EditorGenerationRuntimeSessionV1: ...
```

It branches exactly once on the exact `ProviderChoiceV1`; this is composition,
not routing. It opens only the selected provider. The unselected composer or
factory is not invoked. It creates exactly one `ProviderSelectorV1`, registers
exactly one selected executor, creates the frozen workflow/bridge composition,
mints the runtime authority atomically, then calls the adapter dependency
factory with the exact coordinator operation reference and creates the adapter
with the exact injected fingerprint authority.
The operation reference is identity input only; no execution request or
deterministic artifact is passed to or retained by the adapter. Composition
failure closes any acquired selected resource exactly once before returning the
fixed `Editor generation runtime composition failed.` error.

Factory construction is inert. Only explicit `open(options,
operation_reference=...)` may compose the selected provider, create resources,
create the operation-scoped adapter dependencies and recorder, mint the runtime
authority, create the adapter, and publish the session. `options` is exact
`EditorGenerationRuntimeOptionsV1`; `operation_reference` is an exact built-in,
nonempty, unpadded NFC string of at most 120 characters. Provider selection is
only `options.provider`, with exact `ProviderChoiceV1.OPENAI` or
`ProviderChoiceV1.OLLAMA`; there is no string input, alias, default, case fold,
normalization, discovery, routing, or fallback.

Construction is atomic. Before publication the factory retains each acquired
owned lifecycle authority privately. If any later construction step fails, it
closes only those acquired owned authorities, once each, in reverse acquisition
order, discards all raw failures, and raises the fixed composition error from no
cause or context. Externally injected factories and authorities are never
closed. `open` performs no provider/workflow/adapter execution, generator call,
request construction, JSON validation, retry, timeout enforcement, cancellation
poll, smoke prompt, model discovery/pull, persistence, Producer, or observer
call. OpenAI credentials may be accessed only inside the selected verified
OpenAI composer during explicit OpenAI `open`; the Ollama path never invokes
that factory.

OpenAI composition is exact and additive:

1. `EditorOpenAIRuntimeComposerFactoryV1.create(model_identifier,
   timeout_seconds)` returns one verified `OpenAIRuntimeComposerV2` configured
   with that model, timeout, enabled true, and zero retries;
2. call `compose()` once and retain its `OpenAIRuntimeCompositionV2` as the sole
   lifecycle owner;
3. construct one verified `OpenAIExecutionConfigV2` with the exact model,
   temperature, maximum output tokens, and empty stops;
4. construct one verified `OpenAIProviderExecutorV2` from the composition's
   exact `sdk_client` and that execution config; and
5. register this executor, not the composer's model-only executor. The unused
   executor is never executed and owns no resource. The retained composition
   alone closes the SDK client.

This is necessary because the frozen `OpenAIRuntimeConfigV2` exposes model and
timeout but not generation controls, while the frozen public executor config
does expose them. No private OpenAI helper, raw SDK resource, credential, or
client construction is accessed by these packages.

Ollama composition is exact: `EditorOllamaRuntimeFactoryV1.open(options)`
constructs one owned `httpx.Client`, one verified `OllamaHttpClientV1`, and one
verified `OllamaProviderExecutorV1` with exact model, temperature, maximum
tokens, empty stops, and the separately injected fixed endpoint configuration.
It returns the executor plus one idempotence-guarded close authority for that
same HTTP client. Parser, adapter, coordinator, and selector never own it.

`EditorGenerationRuntimeSessionV1` has private exact references to
`ScoutWorkflowExecutionV1`, `EditorGenerationRuntimeAuthorityV1`,
`EditorNeutralLanguageModelProviderV1`, the exact operation-scoped
`EditorGenerationAttemptRecorderV1`, the operation reference, and the selected
lifecycle authority. Its complete public surface is exactly:

```python
@property
def workflow(self) -> ScoutWorkflowExecutionV1: ...

@property
def runtime_authority(self) -> EditorGenerationRuntimeAuthorityV1: ...

@property
def adapter(self) -> EditorNeutralLanguageModelProviderV1: ...

@property
def attempt_recorder(self) -> EditorGenerationAttemptRecorderV1: ...

@property
def operation_reference(self) -> str: ...

@property
def is_closed(self) -> bool: ...

def close(self) -> None: ...
```

The first four properties return the exact retained identities without copies,
proxies, or adapter traversal. While open, access performs no execution,
snapshot, attempt creation, or cleanup. After close, `workflow`,
`runtime_authority`, `adapter`, and `attempt_recorder` raise
`EditorGenerationRuntimeCompositionError("Editor generation runtime session is
closed.")`. The non-authority values `operation_reference` and `is_closed`
remain readable after close so ownership and diagnostics can be established
without reopening the session. `is_closed` is exact bool.

The recorder protocol remains runtime-package-private and absent from
`__all__`; its exact instance crosses the package boundary only as the return
value of the public `attempt_recorder` property. Revision 3D uses that property
and its normative `snapshot()` method without importing a private helper or
traversing adapter internals.

`close() -> None` transitions the private lifecycle atomically from open to
closed and invokes the selected lifecycle authority exactly once. A second
call raises `EditorGenerationRuntimeCompositionError("Editor generation runtime
session is already closed.")` without a second lower close. There is no public
closing state and no reopening. Context management (`__enter__`, `__exit__`,
`__aenter__`, and `__aexit__`) is not supported; the future coordinator owns
one explicit `close()` in `finally`. The session is identity-only,
address-free in repr, copy/deepcopy return identity, and pickle is rejected
before resource traversal.

### 4.7 Definitive runtime package and public API

Revision 3C.1 creates exactly:

```text
src/pastila_scout/editor_generation_runtime_v1/
    __init__.py
    composition.py
    errors.py
    models.py
    protocols.py
tests/test_editor_generation_runtime_v1.py
```

There is no `session.py` or `factory.py`. `composition.py` owns the public
session and session factory implementation; `models.py` owns only exact private
runtime values; `protocols.py` owns only private injected protocols.

The exact ordered package API is:

```python
__all__ = (
    "EditorGenerationRuntimeCompositionError",
    "EditorGenerationRuntimeSessionFactoryV1",
    "EditorGenerationRuntimeSessionV1",
)
```

There is no alias or second error. In particular,
`EditorGenerationRuntimeConfigurationError` does not exist and a controlled
generator factory is not a runtime public symbol.

`EditorGenerationRuntimeCompositionError` subclasses `Exception`, has no extra
fields, and owns exactly these fixed messages:

```text
Editor generation runtime composition failed.
Editor generation runtime session is closed.
Editor generation runtime session is already closed.
```

Every translated error is raised with `__cause__ is None`, `__context__ is
None`, and `__suppress_context__ is True`. Validation and resource exceptions
are discarded in private outcome functions before the public error is raised;
no public error or package traceback retains a dependency, resource, recorder,
operation reference, provider detail, or raw exception.

### 4.8 Operation-scoped dependencies and attempt provenance

`EditorAdapterDependenciesV1` is a private frozen/slotted bundle with exact
fields `clock`, `cancellation_source`, `reference_factory`, and
`attempt_recorder`. `EditorAdapterDependencyFactoryV1.create`, called once per
session with the exact operation reference, returns one fresh bundle. The
factory and session retain the same recorder identity passed to
`EditorNeutralLanguageModelProviderV1`; no second recorder, wrapper, copy, or
proxy exists.

The recorder implements the already specified exact methods:

```python
def record(self, observation: EditorGenerationAttemptObservationV1) -> None: ...
def snapshot(self) -> tuple[EditorGenerationAttemptObservationV1, ...]: ...
```

It is operation-scoped, append-only, and validates/reconstructs every
observation. Snapshots are immutable ordered tuples with contiguous attempt
numbers starting at one, no duplicates or gaps, and distinct request
references. The recorder is bound to the session operation reference through
the same private reference factory used by the adapter. Thus every recorded
attempt belongs to that one operation authority even though the safe public
observation deliberately does not duplicate the operation-reference text.
Property access and snapshot perform no provider execution and create no
attempt. The coordinator reads a snapshot only after generation and never
records, mutates, fabricates, or recomputes an observation.

The remaining private runtime composition values are exact:

```python
class _EditorRuntimeLifecycleAuthorityV1(Protocol):
    def close(self) -> None: ...

@dataclass(frozen=True, slots=True)
class EditorOllamaRuntimeHandleV1:
    executor: ProviderExecutorV2
    lifecycle: _EditorRuntimeLifecycleAuthorityV1

@dataclass(frozen=True, slots=True)
class EditorAdapterDependenciesV1:
    clock: EditorGenerationClockV1
    cancellation_source: EditorGenerationCancellationSourceV1
    reference_factory: EditorGenerationReferenceFactoryV1
    attempt_recorder: EditorGenerationAttemptRecorderV1
```

Both bundles are package-private, absent from `__all__`, exact-type validated,
slotted, address-free, and reject pickle. The Ollama handle owns only the
lifecycle explicitly returned by the injected Ollama factory. For OpenAI, the
exact `OpenAIRuntimeCompositionV2` returned by the verified composer is the
lifecycle authority and its `sdk_client` is used only to construct the
option-complete verified executor; the runtime session retains no separately
closable SDK/client reference. Lifecycle `close()` is the only private cleanup
shape. It is statically validated and invoked only by construction rollback or
session close.

## 5. Structured-output authority

The schema source is exactly the `output_schema` class supplied by
`ControlledGenerator`. It MUST be one of the existing component result models:
`StoryGenerationResult`, `TransitionGenerationResult`,
`OpeningGenerationResult`, `ClosingGenerationResult`, or
`CallToActionGenerationResult`.

The adapter calls `output_schema.model_json_schema()` once. Canonical schema JSON
is `json.dumps(schema, ensure_ascii=False, sort_keys=True,
separators=(",", ":"), allow_nan=False)` after recursively rejecting non-string
keys and non-JSON primitives. Its fingerprint is lowercase SHA-256 over the
canonical UTF-8 bytes. Schema name is exact `output_schema.__name__`.

The existing `PromptBuilder` already embeds the schema in the ordered
`OUTPUT_SCHEMA` section. The adapter MUST use `GenerationPrompt.text` exactly;
it adds no second schema text. The schema name, canonical JSON, and fingerprint
are also identity authority in `EditorGenerationApplicationRequestV1`, but
because frozen lower DTOs lack schema fields they are not sent as a provider
option. Structured enforcement is application-owned strict JSON-mode
validation.

### 5.1 Sole structured-output validation path

The generated text is passed byte-for-byte unchanged to exactly one call:

```python
output_schema.model_validate_json(generated_text, strict=True)
```

This call is the sole structured-output parsing and validation path. Pydantic
owns the one JSON parse internally and performs the one schema validation in
JSON strict mode. The adapter performs zero explicit `json.loads` calls and
MUST NOT trim, normalize, repair, unwrap Markdown, extract a code block,
pre-convert lists to tuples, coerce values, invoke non-strict validation, or
attempt a fallback or second parse.

Strict JSON mode deliberately preserves the frozen Editor models. JSON arrays
are accepted for tuple-typed fields according to Pydantic JSON-mode strict
semantics and are returned as tuples in the exact validated frozen model. This
applies to empty arrays, nonempty arrays, and nested tuple fields. Invalid
element types and wrong root shapes remain schema-validation failures.

One `pydantic.ValidationError` is classified using only its safe structured
error type. A sole `json_invalid` error maps to
`ProviderStructuredOutputError("Provider returned malformed structured
output.")`. Any other validation error maps to
`ProviderStructuredOutputError("Provider returned structured output that failed
schema validation.")`. These are the exact fixed messages. Neither mapping
exposes generated text, raw Pydantic messages, input values, locations derived
from provider content, or a chained exception. Classification may inspect
`errors(include_url=False, include_context=False, include_input=False)` exactly
once; it MUST retain or expose none of that temporary structure. The adapter
does not use a second parser to distinguish these categories.

For one successful adapter call, generated-text extraction occurs once,
`model_validate_json(..., strict=True)` occurs once, Pydantic owns exactly one
JSON parse and one schema validation, and explicit `json.loads`, preprocessing,
repair, fallback parsing, and fallback validation each occur zero times.

OpenAI and Ollama receive the identical single generation message. Neither
receives a native schema option. If future policy requires native provider
schema enforcement, both paths fail closed until the neutral contract and both
verified providers support it; no provider-specific editorial branch is allowed.

## 6. Deterministic enrichment and execution request

This entire section is coordinator-level authority for future Revision 3D.
Neither package nor value in this section is imported, accepted, retained,
reconstructed, or fabricated by the Revision 3C provider adapter.

### 6.1 `EditorGenerationPreparationCoordinatorV1`

Constructor dependencies, in order:

```python
flow_optimizer: EpisodeFlowOptimizerV1
editorial_builder: EditorialBlueprintBuilderV1
commentary_builder: CommentaryBlueprintBuilderV1
voice_builder: VoiceModelBuilderV1
```

These protocols reproduce the exact existing method signatures and return
annotations. Dependencies are statically validated without invocation.

Exact method:

```python
def enrich(
    self,
    preparation: EditorOperationalPreparationResultV1,
    options: EditorGenerationRuntimeOptionsV1,
    provider: ProviderChoiceV1,
    requested_at: datetime,
    request_reference: str,
    cancellation: CancellationTokenV2,
) -> EditorGenerationExecutionRequestV1: ...
```

It requires a successful Revision 2 lifecycle, no failure, and one reconstructed
plan. Provider MUST equal options provider. Exact call order and cardinality:

1. rebuild `EditorialSelectionResult(plan.selection_output,
   plan.selection_trace)` locally;
2. call `flow_optimizer.optimize` once;
3. strictly reconstruct and cross-validate `FlowOptimizationResult`;
4. call `editorial_builder.build` once and retain `.blueprint`;
5. reconstruct output/blueprint/trace and verify output equals flow output;
6. call `commentary_builder.build` once and retain `.blueprint`;
7. reconstruct and verify output and flow order;
8. call `voice_builder.build` once and retain `.plan`;
9. reconstruct and verify output and flow order; and
10. construct/reconstruct the execution request.

Any failure produces the fixed error `Editor generation preparation failed.`
from no cause. No provider is selected or executed.

### 6.2 `EditorGenerationExecutionRequestV1`

Fields, in order, all required:

```python
preparation: EditorOperationalPreparationResultV1
plan: EditorGenerationPlanV1
flow_result: FlowOptimizationResult
editorial_blueprint: EditorialBlueprint
commentary_blueprint: EpisodeCommentaryBlueprint
voice_plan: EpisodeVoicePlan
generation_configuration: LanguageGenerationConfig
runtime_options: EditorGenerationRuntimeOptionsV1
provider: ProviderChoiceV1
requested_at: datetime
request_reference: str
cancellation: CancellationTokenV2
request_fingerprint: str
```

The plan MUST equal preparation.plan. Every nested value is exact-type strictly
reconstructed. All public outputs in deterministic artifacts MUST equal
plan.selection_output after the flow optimizer's authoritative output is
propagated, and must pass existing cross-validation. Flow orders across flow
output, editorial blueprint, commentary blueprint, and voice plan MUST be
identical to the selected story order. All event IDs must originate in the
plan's source input.

Generation configuration MUST map exactly to runtime options: provider string
equals provider value; model/revision, numeric-type/value temperature/top-p,
max tokens, seed, structured mode, and timeout equal exactly. The current
configuration has no stop field, so runtime stops MUST be empty. Provider and
options provider match. Request fingerprint covers every preceding field by
canonical JSON and binds the Revision 2 plan seal through its public semantic
fields; no private seal is serialized.

## 7. ControlledGenerator mapping

The execution coordinator constructs `ControlledGenerator` exactly once using:

```python
ControlledGenerator(
    provider=neutral_adapter,
    config=request.generation_configuration,
    policy=GenerationPolicy(),
    prompt_builder=PromptBuilder(),
)
```

No alternate policy or prompt builder is permitted in V1. It invokes
`generate` exactly once with:

```python
scout_input=request.plan.source_input
selection_profile=request.plan.selection_profile
episode_context=request.plan.episode_context
flow_result=request.flow_result
editorial_blueprint=request.editorial_blueprint
commentary_blueprint=request.commentary_blueprint
voice_plan=request.voice_plan
static_cta_content=""
teleprompter_profile=None
```

The generator remains sole owner of component prompt construction, schema
choice, component validation, generation state, manifest, assembly, formatting,
editorial corrective attempts, and its documented timeout retry. The
coordinator MUST NOT duplicate or reinterpret them.

## 8. Provider-neutral `LanguageModelProvider` adapter

The Revision 3C flow is exactly:

```text
ControlledGenerator
  -> LanguageModelProvider.generate_structured(
       GenerationPrompt, output_schema, LanguageGenerationConfig)
  -> GenerationPrompt.text
  -> EditorGenerationApplicationRequestV1
  -> EditorGenerationRequestAuthorityV1
  -> ProviderExecutionRequestV2
  -> ScoutRuntimeRequestV1
  -> ScoutWorkflowExecutionV1.execute_provider_neutral
  -> generated text
  -> output_schema.model_validate_json(generated_text, strict=True) exactly once
  -> validated Pydantic model
```

The adapter MUST NOT construct, accept, retain, reconstruct, or depend on
`EditorGenerationExecutionRequestV1`, `EditorOperationalPreparationResultV1`,
`EditorGenerationPlanV1`, `FlowOptimizationResult`, `EditorialBlueprint`,
`EpisodeCommentaryBlueprint`, or `EpisodeVoicePlan`.

### 8.1 `EditorNeutralLanguageModelProviderV1`

It satisfies the existing protocol and has exact public field:

```python
provider_identifier: str
```

Constructor dependencies:

```python
def __init__(
    self,
    *,
    provider: ProviderChoiceV1,
    workflow: ScoutWorkflowExecutionV1,
    runtime_authority: EditorGenerationRuntimeAuthorityV1,
    fingerprint_authority: EditorRequestFingerprintAuthorityV1,
    request_authority: EditorGenerationRequestAuthorityV1,
    requested_at_factory: EditorGenerationClockV1,
    cancellation_source: EditorGenerationCancellationSourceV1,
    request_reference_factory: EditorGenerationReferenceFactoryV1,
    attempt_recorder: EditorGenerationAttemptRecorderV1,
) -> None: ...
```

Every callable protocol has an exact annotated signature and is statically
validated. The workflow must be exact `ScoutWorkflowExecutionV1`; adapter code
does not access its bridge, selector, or executor.

The constructor contains only adapter-level dependencies. It has no execution
request, preparation result, generation plan, deterministic artifact, setter,
late injection method, registry, or runtime lookup.

The exact fingerprint dependency is the public
`EditorRequestFingerprintAuthorityV1`. The adapter validates its exact type
without invoking it during construction and passes it to the package-private
application-request builder. The adapter never implements canonicalization or
SHA-256 itself.

Exact method signature is the existing protocol signature:

```python
def generate_structured(
    self,
    *,
    prompt: GenerationPrompt,
    output_schema: type[T],
    config: LanguageGenerationConfig,
) -> T: ...
```

Execution steps:

1. reconstruct exact prompt/config and validate output-schema allowlist;
2. prove config exactly matches runtime authority;
3. derive canonical schema once under section 5;
4. obtain one aware timestamp, fresh cancellation snapshot, and unique reference;
5. call the package-private application-request builder once using
   `prompt.text`, reconstructed options/schema authority, timestamp, reference,
   and cancellation; the builder calls the public fingerprint authority once
   and returns one reconstructed `EditorGenerationApplicationRequestV1`;
6. build one `ProviderExecutionRequestV2` through the new authority;
7. wrap it in `ScoutRuntimeRequestV1(True, lower_request)`;
8. call `workflow.execute_provider_neutral` exactly once;
9. reconstruct `ScoutRuntimeResultV1` and validate request/provider/envelope and
   output source-reference lineage;
10. record one safe attempt observation;
11. require completed execution, successful provider result, exactly one output,
    ordinal zero, and completed finish reason;
12. copy `generated_text` exactly without inspecting, trimming, or changing it;
13. call `output_schema.model_validate_json(generated_text, strict=True)` exactly
    once, allowing Pydantic to perform the sole JSON parse and strict schema
    validation;
14. safely distinguish Pydantic `json_invalid` from other validation failures
    without a second parse or raw diagnostic exposure; and
15. return that exact validated frozen model.

`GenerationPrompt` has no system/user-message pair. Its authoritative textual
serialization is its frozen `text` property: ordered sections joined exactly by
two LF characters, with each section rendered as
`[<layer>] <title>\n<content>`. The adapter reconstructs the exact prompt model,
then reads `prompt.text` once and passes that exact string to
`EditorGenerationApplicationRequestV1`. It adds no role, message, system
content, wrapper, separator, or absence marker. The generation authority alone
performs its verified single NFC semantic canonicalization for the lower
message; the adapter performs none.

The application-request mapping is exact:

| Application field | Source |
|---|---|
| provider | injected exact `ProviderChoiceV1`, equal to config/runtime authority |
| prompt | exact `GenerationPrompt.text` |
| request reference | injected reference factory output for the current attempt |
| requested at | one aware timestamp from the injected clock |
| options | exact reconstructed runtime authority options, proven equal to config |
| schema name | exact allowlisted `output_schema.__name__` |
| canonical schema JSON | section 5, computed once |
| schema fingerprint | section 5 SHA-256 |
| cancellation | one fresh injected cancellation snapshot |
| request fingerprint | Revision 3B canonical application-request authority |

Config mapping is exact for provider, model identifier/revision, numeric type
and value of temperature/top-p, maximum output tokens, seed, structured-output
mode, and timeout. Stops remain the exact empty runtime tuple because the frozen
generation config has no stop field. No option is inferred, defaulted, dropped,
normalized, or provider-specialized.

No trim, normalization after authority, Markdown handling, fence stripping,
repair, preprocessing, list-to-tuple conversion, coercion, retry, fallback,
explicit `json.loads`, second parse, or provider branch is permitted. Invalid
JSON syntax maps to the fixed malformed structured-output error. Syntactically
valid JSON that fails the frozen model maps to the fixed structured
schema-validation error. The exact class/messages are defined in section 5.1.
Both are raised from no cause and expose no raw Pydantic or provider content.
Provider failure maps to the existing safe
Provider error class. Timeout maps to `ProviderTimeoutError`, cancellation to a
new non-timeout `ProviderCancellationError` subclass of `ProviderError`, and
malformed/lineage/internal failures to fixed safe provider errors. Raw lower
messages are never retained.

### 8.2 Application-request construction boundary

`application_request.py` defines package-private
`_EditorGenerationApplicationRequestBuilderV1`. It is not exported. Its exact
constructor and method are:

```python
def __init__(
    self,
    fingerprint_authority: EditorRequestFingerprintAuthorityV1,
) -> None: ...

def build(
    self,
    *,
    provider: ProviderChoiceV1,
    prompt: str,
    request_reference: str,
    requested_at: datetime,
    options: EditorGenerationRuntimeOptionsV1,
    output_schema_name: str,
    output_schema_canonical_json: str,
    output_schema_fingerprint: str,
    cancellation: CancellationTokenV2,
) -> EditorGenerationApplicationRequestV1: ...
```

The builder statically validates and retains only the exact stateless
fingerprint authority. For each explicit `build` call it:

1. reconstructs the nine semantic inputs using public contract behavior;
2. calls `fingerprint_authority.fingerprint` exactly once with those same nine
   values in the exact keyword order above;
3. constructs `EditorGenerationApplicationRequestV1` exactly once with those
   values followed by the returned digest;
4. reconstructs the request through its public copy behavior;
5. requires every reconstructed semantic field to equal the authoritative
   input and its fingerprint to equal the authority result using
   `hmac.compare_digest`; and
6. returns the reconstructed request.

It performs no independent canonicalization, hashing, schema construction,
provider selection/execution, retry, clock/cancellation acquisition, or lower
request construction. It accepts no caller-supplied request fingerprint. A
fingerprint-authority error, invalid returned digest, request-construction
failure, copied-invalid request, or coordinated field/fingerprint substitution
maps to fixed `EditorGenerationProviderAdapterError("Editor generation provider
adapter failed.")` outside an active exception context with no retained cause.

The builder is the application-request construction boundary for Revision 3C.
It is package-private because it is an implementation detail of the one public
adapter, not a second application policy API. This closes the construction path
without changing or weakening frozen Revision 3B.

### 8.3 Attempt observation

`EditorGenerationAttemptObservationV1` fields:

```python
attempt_number: int
prompt_fingerprint: str
request_reference: str
request_fingerprint: str
execution_request_id: str
request_envelope_identity: str
provider_id: str
outcome: ExecutionOutcomeV2
source_output_reference: str | None
finish_reason: ProviderFinishReasonV2 | None
failure_code: str | None
```

It contains no text, prompt, schema, client, exception, or provider result.
`EditorGenerationAttemptRecorderV1.record(observation) -> None` is per operation,
injected, and append-only. Recorder failure is terminal internal failure; it is
never ignored because result attempt provenance depends on it.

Before constructing an application request, the adapter calls `snapshot()`
once, reconstructs every existing observation, requires attempt numbers exactly
`1..N`, and sets the current `attempt_number` to `N + 1`. It then calls
`request_reference_factory.create(prompt_fingerprint=prompt.prompt_fingerprint,
attempt_number=attempt_number)` exactly once. The factory is operation-scoped
and is seeded by composition with the exact coordinator
`operation_reference` passed under section 4.6; the
adapter neither sees nor fabricates coordinator lineage. The returned reference
must be fresh relative to the snapshot. A duplicate, gap, reordering, prompt
fingerprint mismatch for a timeout retry, or invalid snapshot fails before
lower execution. The adapter owns no mutable attempt counter.

One provider call has exact cardinality:

```text
one ControlledGenerator provider call
  = one adapter invocation
  = one EditorGenerationApplicationRequestV1
  = one ProviderExecutionRequestV2
  = one lower provider execution
```

If `ControlledGenerator` retries after timeout, it invokes the adapter again.
That second invocation obtains a fresh timestamp, cancellation snapshot,
attempt number, application reference, application request, lower request, and
lower execution. `EditorGenerationExecutionRequestV1` remains unchanged at the
coordinator layer across both calls.

### 8.4 Separate lineage layers

Adapter-level lineage is owned only by
`EditorGenerationApplicationRequestV1`, `EditorGenerationRequestAuthorityV1`,
and `ProviderExecutionRequestV2`. It covers prompt and schema authority,
generation options, provider/model, timeout, cancellation, application and
lower request identities, envelope identity, request-unit/output references,
and provider-neutral fingerprints. The adapter validates those exact lower
identities before parsing text.

Coordinator-level lineage is owned only by
`EditorGenerationExecutionRequestV1`,
`EditorOperationalExecutionCoordinatorV1`, and `EditorOperationalResultV1`.
It covers preparation identity, generation-plan identity, deterministic
artifacts, the `ControlledGenerator` operation, adapter attempt observations,
and the final operational result. The adapter never fabricates or interprets
this lineage. The coordinator records safe attempt observations but never
reinterprets lower provider lineage.

## 9. Retry, timeout, cancellation, and cleanup

Repository behavior is normative:

- `ControlledGenerator._provider_call` is the sole timeout retry owner.
- It calls the adapter a second time immediately only after the first raises
  `ProviderTimeoutError`.
- There is no backoff.
- Each adapter call performs exactly one lower workflow execution.
- Each lower attempt has its own `TimeoutPolicyV2`; no total timer exists.
- Timestamp, reference, lower request, envelope, and cancellation snapshot are
  fresh for every adapter call.
- The same composed workflow/runtime/executor is reused for the operation.
- Before each dispatch the fresh cancellation snapshot is checked. Cancellation
  before the first dispatch performs zero lower calls. Cancellation before the
  timeout retry prevents the retry and takes precedence over timeout.
- Non-timeout Provider errors are not retried by `_provider_call`. Existing
  component schema/semantic corrective attempts remain separately owned by
  `ControlledGenerator` and bounded by `GenerationPolicy`.

`EditorGenerationRuntimeSessionV1` is the application composition owner. It
contains the exact workflow, runtime authority, adapter, and one idempotence
guarded `close() -> None`. It owns the underlying verified runtime. The
execution composition root opens one session before `ControlledGenerator` and
closes it exactly once in `finally` after success, terminal failure,
cancellation, or retry exhaustion. It never closes between attempts. The
coordinator and adapter have no close method and never traverse resources.

## 10. Execution coordinator

`EditorOperationalExecutionCoordinatorV1` is future Revision 3D and is separate
from Revision 2 and the Revision 3C adapter. It is the sole consumer of
`EditorGenerationExecutionRequestV1`.

Constructor:

```python
def __init__(
    self,
    *,
    session_factory: EditorGenerationRuntimeSessionFactoryV1,
    generator_factory: _EditorControlledGeneratorFactoryV1,
) -> None: ...
```

`_EditorControlledGeneratorFactoryV1` is owned by the future
`editor_operational_execution_v1.protocols` module, not the runtime package.
It is package-private inside the same package as its coordinator consumer and
is absent from every public `__all__`. The public session factory is the only
cross-package constructor dependency. This removes the former requirement for
Revision 3D to import a private runtime protocol.

Exact method:

```python
def execute(
    self,
    request: EditorGenerationExecutionRequestV1,
) -> EditorOperationalResultV1: ...
```

Dependencies are statically validated without execution. Execution order:

1. reconstruct request; invalid deterministic artifacts return pre-dispatch
   failure with zero session/generator/provider calls;
2. create one runtime session for exact request options/provider and pass
   `request.request_reference` as its `operation_reference`;
3. create one adapter bound to the session and one generator using section 7;
4. invoke `ControlledGenerator.generate` exactly once;
5. reconstruct `ControlledGenerationResult` and its draft, trace, manifest, and
   final state;
6. snapshot recorder observations and retain only a private candidate outcome;
7. close the session once;
8. construct/reconstruct `EditorOperationalResultV1` only after the close
   outcome is known; and
9. if an earlier step raises, close once in `finally`, then construct the safe
   failed/cancelled result from the retained candidate state.

The coordinator never publishes a completed result before cleanup. Cleanup
failure converts a would-be completion to `cleanup_failed`. When cleanup fails
after another terminal failure, the primary failure remains authoritative and
`cleanup_failed=True` records the additional safe fact.

The coordinator performs no deterministic selection/enrichment, provider
selection policy, raw client access, retry loop, timeout enforcement,
cancellation polling, persistence, CLI, Producer, or output rendering.

## 11. Lifecycle and failures

`EditorOperationalGenerationStatusV1` values, in order:

```text
completed
failed
cancelled
```

`EditorOperationalGenerationLifecycleStateV1` values, in order:

```text
accepted, validated, session_opened, generation_started, generated,
result_validated, completed, failed, cancelled
```

Valid lifecycle tuples are closed:

- completed: accepted, validated, session_opened, generation_started,
  generated, result_validated, completed;
- invalid request/artifacts: accepted, failed;
- session failure: accepted, validated, failed;
- generation/provider/internal failure: accepted, validated, session_opened,
  generation_started, failed;
- cancellation: the applicable success prefix through generation_started,
  followed by cancelled;
- invalid controlled result: prefix through generated, followed by failed.

`EditorOperationalGenerationFailureCodeV1` values and exact messages:

| Code | Message | Retryable |
|---|---|---|
| `invalid_execution_request` | `Editor generation request is invalid.` | false |
| `deterministic_artifact_invalid` | `Editor deterministic generation artifact is invalid.` | false |
| `runtime_composition_failed` | `Editor generation runtime composition failed.` | false |
| `provider_failed` | `Editor generation provider failed.` | false |
| `timeout_exhausted` | `Editor generation timed out.` | false |
| `cancelled` | `Editor generation was cancelled.` | false |
| `malformed_provider_result` | `Editor provider result is malformed.` | false |
| `invalid_provider_lineage` | `Editor provider result lineage is invalid.` | false |
| `malformed_generated_json` | `Editor generated JSON is malformed.` | false |
| `generated_schema_invalid` | `Editor generated schema is invalid.` | false |
| `controlled_generation_failed` | `Editor controlled generation failed.` | false |
| `controlled_result_invalid` | `Editor controlled generation result is invalid.` | false |
| `internal_execution_failure` | `Editor generation execution failed.` | false |
| `cleanup_failed` | `Editor generation cleanup failed.` | false |

`EditorOperationalGenerationFailureV1` fields are `code`, `safe_message`, and
`retryable=False`. No raw lower code/message is public. Cleanup failure overrides
a would-be completed result because resource ownership did not terminate
successfully; it does not replace cancellation or an existing execution failure,
but is retained only as an additional safe cleanup flag in diagnostics.

There is no partial draft. Any failed/cancelled outcome has no draft, generation
trace, manifest, or final state and prohibits downstream handoff.

Because frozen `ControlledGenerator` wraps provider exceptions, terminal
classification is derived only from the operation-scoped safe attempt record,
never from exception text or traceback. If the final observation is cancelled,
the result is cancelled. If the final two immediately consecutive observations
have the same prompt fingerprint and both are timeout, the result is
`timeout_exhausted`. A malformed/lineage/JSON/schema/provider observation maps
to its corresponding closed failure code. If no safe observation proves a more
specific category, the result is `controlled_generation_failed` or
`internal_execution_failure` according to the failing boundary. Earlier
observations never override the final attempt.

## 12. `EditorOperationalResultV1`

Fields, in order, all required:

```python
source_report_id: str
source_report_fingerprint: str
preparation_result_fingerprint: str
execution_request_reference: str
execution_request_fingerprint: str
status: EditorOperationalGenerationStatusV1
lifecycle: tuple[EditorOperationalGenerationLifecycleStateV1, ...]
draft: EpisodeDraft | None
generation_trace: GenerationTrace | None
generation_manifest: GenerationManifest | None
final_state_revision: int | None
attempts: tuple[EditorGenerationAttemptObservationV1, ...]
attempt_count: int
timeout_retry_count: int
failure: EditorOperationalGenerationFailureV1 | None
cleanup_failed: bool
result_fingerprint: str
```

Lineage fields equal the reconstructed request/preparation/plan. Preparation
fingerprint is canonical SHA-256 over the public semantic Revision 2 result.
Attempt count equals tuple length; attempt numbers are contiguous from one.
Timeout retry count is the number of observations immediately following a
timeout with the same `prompt_fingerprint`. Attempt numbers are operation-global
and contiguous. A retry observation MUST immediately follow its timeout and
share the exact prompt fingerprint; no other pairing counts. Timeout retry count
cannot exceed the number of timeout observations. No fabricated provider
request metadata is allowed.

Completed status requires the exact completed lifecycle; reconstructed draft,
trace, manifest and final revision; at least one successful attempt; no failure;
and `cleanup_failed=False`. Failed/cancelled requires all generated output fields
absent and one matching failure. Cancelled has the cancelled code/lifecycle.
Failed may have zero attempts pre-dispatch. `cleanup_failed` is exact bool.

Result fingerprint is SHA-256 over canonical UTF-8 JSON of every preceding
field. Canonicalization follows section 4.3 and includes full validated draft
and safe trace/manifest but excludes private attributes. Equality compares
exact reconstructed fields. It is frozen/slotted. Copy/deepcopy produce fresh
reconstructed equal values. Pickle is rejected. Repr exposes only status,
attempt count, timeout retry count, and cleanup flag; it contains no identity,
text, output, failure message, dependency, or address.

## 13. Observer, persistence, and Producer

Revision 3 has no observer. Existing lower diagnostics remain internal and only
the safe attempt observations in the result are exposed. No event sink or
observer field exists.

Revision 3 performs zero filesystem/database persistence and zero Producer
handoff. The result is returned in memory to the caller. Failed, cancelled, or
cleanup-failed results cannot be handed downstream.

## 14. Public APIs

### `editor_generation_authority_v1.__all__`

```python
(
    "EditorGenerationApplicationRequestV1",
    "EditorGenerationAuthorityError",
    "EditorGenerationRequestAuthorityV1",
    "EditorGenerationRuntimeAuthorityV1",
    "EditorGenerationRuntimeOptionsV1",
)
```

### `editor_generation_execution_v1.__all__`

```python
("EditorGenerationExecutionRequestV1",)
```

This is the exact frozen Revision 3B public API. The future deterministic
preparation coordinator and its error are not Revision 3B exports and must not
be imported by Revision 3C.

### `editor_generation_provider_adapter_v1.__all__`

```python
(
    "EditorGenerationAttemptObservationV1",
    "EditorGenerationProviderAdapterError",
    "EditorNeutralLanguageModelProviderV1",
)
```

### `editor_operational_execution_v1.__all__`

```python
(
    "EditorOperationalExecutionConfigurationError",
    "EditorOperationalExecutionCoordinatorV1",
    "EditorOperationalGenerationFailureCodeV1",
    "EditorOperationalGenerationFailureV1",
    "EditorOperationalGenerationLifecycleStateV1",
    "EditorOperationalGenerationStatusV1",
    "EditorOperationalResultV1",
)
```

### `editor_generation_runtime_v1.__all__`

```python
(
    "EditorGenerationRuntimeCompositionError",
    "EditorGenerationRuntimeSessionFactoryV1",
    "EditorGenerationRuntimeSessionV1",
)
```

Protocol and factory types are package-private unless explicitly promoted by a
later independently reviewed composition specification. No SDK, concrete
provider, CLI, persistence, registry, service locator, runtime-discovery helper,
or private frozen helper is exported.

### 14.1 Exact private dependency protocols

These protocols are normative even though they are not exported. Each uses an
ordinary instance method and the exact signature shown:

```python
class EditorGenerationClockV1(Protocol):
    def now(self) -> datetime: ...

class EditorGenerationCancellationSourceV1(Protocol):
    def snapshot(self) -> CancellationTokenV2: ...

class EditorGenerationReferenceFactoryV1(Protocol):
    def create(self, *, prompt_fingerprint: str, attempt_number: int) -> str: ...

class EditorGenerationAttemptRecorderV1(Protocol):
    def record(self, observation: EditorGenerationAttemptObservationV1) -> None: ...
    def snapshot(self) -> tuple[EditorGenerationAttemptObservationV1, ...]: ...

class _EditorControlledGeneratorFactoryV1(Protocol):
    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> ControlledGenerator: ...

class EditorOpenAIRuntimeComposerFactoryV1(Protocol):
    def create(
        self, *, model_identifier: str, timeout_seconds: int | float
    ) -> OpenAIRuntimeComposerV2: ...

class EditorOllamaRuntimeFactoryV1(Protocol):
    def open(
        self, options: EditorGenerationRuntimeOptionsV1
    ) -> EditorOllamaRuntimeHandleV1: ...

class EditorScoutWorkflowFactoryV1(Protocol):
    def create(
        self, *, provider: ProviderChoiceV1, selected_executor: ProviderExecutorV2
    ) -> ScoutWorkflowExecutionV1: ...

class EditorAdapterDependencyFactoryV1(Protocol):
    def create(self, *, operation_reference: str) -> EditorAdapterDependenciesV1: ...
```

`EditorOllamaRuntimeHandleV1` contains exact private executor and lifecycle
authorities and exposes neither publicly. `EditorAdapterDependenciesV1` is a
frozen private bundle containing exactly one clock, cancellation source,
reference factory, and recorder. Its factory returns fresh operation-scoped
dependencies; no dependency is global or shared between sessions.
The dependency factory validates the unpadded operation reference and binds it
privately into the reference factory. Application references are deterministic
functions of that operation reference, prompt fingerprint, and attempt number;
the coordinator reference is not exposed to the adapter.

The deterministic protocols reproduce these discovered public call shapes
without adding parameters: `EpisodeFlowOptimizerV1.optimize(scout_input,
profile, context, selection_result) -> FlowOptimizationResult`;
`EditorialBlueprintBuilderV1.build(scout_input, profile, context, flow_result)
-> BlueprintBuildResult`; `CommentaryBlueprintBuilderV1.build(scout_input,
profile, context, flow_result, editorial_blueprint)` with the exact existing
unannotated return contract; and `VoiceModelBuilderV1.build(scout_input,
profile, context, flow_result, editorial_blueprint, commentary_blueprint) ->
VoiceBuildResult`. Implementation MUST copy the exact annotations (including
their absence), parameter names, and positional/keyword kinds from the inspected
production definitions; these protocols do not authorize signature invention.

Every dependency protocol is validated statically at construction as specified
in section 15. Factories return exact expected types. Returning a subclass,
proxy, copied-invalid value, reused closed handle, or mismatched configuration
fails before execution with the package's fixed configuration error.

### 14.2 Fixed boundary errors

Public boundary errors contain exactly these safe messages and are raised from
no cause:

| Error | Exact message |
|---|---|
| `EditorGenerationAuthorityError` | `Editor generation authority is invalid.` |
| `EditorGenerationPreparationError` | `Editor generation preparation failed.` |
| `EditorGenerationProviderAdapterError` | `Editor generation provider adapter failed.` |
| `EditorGenerationRuntimeCompositionError` | `Editor generation runtime composition failed.` |
| `EditorOperationalExecutionConfigurationError` | `Editor operational execution configuration is invalid.` |

Provider-facing timeout, cancellation, malformed structured output, and safe
provider errors retain the exact classes/messages in section 8. Operational
mapping exposes only section 11 failure values. No raw exception, lower failure
message/code, prompt, output, dependency, or traceback crosses a boundary.

## 15. Object safety and error isolation

Every public value uses frozen, slotted, init-disabled storage with exact public
field order and one private semantic seal. Exact-type validation rejects
primitive subclasses/coercion. Nested existing models are reconstructed by
strict Python-mode dump/validation. Retained seal mismatch, missing state, and
copied-invalid reconstruction fail closed.

Dependency objects use static descriptor validation: ordinary instance methods,
exact names/order/kinds/defaults/annotations, no properties/cached properties,
static/class methods, partials, wrappers, forged signatures, dynamic attributes,
or instance replacements. Validation invokes no body, hook, equality, repr, or
copy behavior.

Value equality compares reconstructed fields. Dependency-bearing equality uses
dependency identity only. Value copy/deepcopy reconstructs; dependency-bearing
copy/deepcopy constructs a new wrapper preserving dependency identities and
never traverses them. All public/internal dependency-bearing objects reject
pickle before traversal. Reprs are fixed, address-free, and content-redacted.

Public application errors have one fixed message per type, no extra attributes,
`__context__ is None`, `__cause__ is None`, and suppression true. Before raising,
package frames delete prompt, schema, Scout input, deterministic artifacts,
request/result, draft, dependencies, clients, and raw exceptions. Recursive
exception graphs and package traceback locals retain none of them.

## 16. Passive behavior

Import and construction perform zero provider execution/selection, credential
access, client construction, networking, generation, retry, clock/timer access,
cancellation polling, cleanup, persistence, filesystem/database access,
threads/subprocesses, logging, warnings, stdout, or stderr. Only explicit
`enrich` invokes deterministic builders. Only explicit `execute` composes a
session and invokes `ControlledGenerator`/neutral runtime.

## 17. Failure/cancellation matrix

| Condition | Lower calls | Retry | Status/output | Cleanup |
|---|---:|---:|---|---:|
| invalid request/artifact | 0 | 0 | failed, no draft | 0 |
| pre-dispatch cancelled | 0 | 0 | cancelled, no draft | session once if opened |
| provider failure | 1 | 0 | failed, no draft | once |
| timeout then success | 2 | 1 | operation continues | once after operation |
| timeout twice | 2 | 1 | failed, no draft | once |
| cancellation before retry | 1 | 0 second dispatch | cancelled, no draft | once |
| malformed lower result/lineage | 1 | 0 | failed, no draft | once |
| malformed JSON/schema | one per existing component attempt | generator policy only | terminal failure has no draft | once |
| controlled result invalid | existing attempts | no coordinator retry | failed, no draft | once |
| cleanup failure after success | existing attempts | none | failed, no public draft | exactly one attempted close |

Cancellation metadata is copied only from fresh caller authority. Lower
cancellation is represented only when a validated lower result reports it. No
configured or inferred cancellation is substituted.

## 18. Adversarial test matrix

Each implementing revision SHALL test, offline:

1. exact exports/order, fields/signatures, forbidden imports;
2. every option classification and exact numeric type/value preservation;
3. rejection of non-default top-p, non-null seed, nonempty stops, false
   structured mode, option/session mismatch;
4. canonical request/schema/result fingerprints and copied-invalid rejection;
5. exact deterministic enrichment call order, one call each, lineage/order;
6. missing/corrupt preparation, plan, artifacts, configuration;
7. malformed dependency descriptors, annotations, properties, partials,
   wrappers, forged signatures, dynamic/instance replacements;
8. exact `GenerationPrompt.text`, schema canonicalization and identity;
9. identical OpenAI/Ollama application semantics and schema fingerprints;
10. one lower execution per adapter invocation;
11. two calls only after timeout, none for other errors, no backoff;
12. fresh reference/request/cancellation per call and cancellation precedence;
13. exact successful text extraction; strict `model_validate_json` acceptance
    of empty, nonempty, and nested tuple-field arrays; invalid tuple elements
    and wrong root rejection; no trim/fence, preprocessing, repair, explicit
    `json.loads`, fallback, or second validation; one Pydantic-owned JSON parse
    and one strict schema validation;
14. provider failure, timeout exhaustion, cancellation, malformed result,
    lineage mismatch, JSON failure, schema failure, internal failure;
15. `ControlledGenerator` constructed/called once and exact argument mapping;
16. exact result lifecycle/failure/output/attempt/cleanup contradictions;
17. session cleanup exactly once on every opened-session path and never between
    attempts;
18. zero observer, persistence, Producer, CLI, fallback, routing;
19. error/traceback graph isolation and content-safe fixed messages;
20. copy/deepcopy/pickle/repr/equality and dependency non-traversal;
21. passive fresh-process imports/construction and offline isolation; and
22. frozen hashes/exports, focused/full suite, Ruff, Black, compileall, pip
    check, and diff check.

Revision 3C specifically tests only adapter-level responsibilities: exact
ordered exports; exact frozen `LanguageModelProvider` signature compatibility;
static dependency validation; exact `GenerationPrompt.text`; schema/options
mapping; OpenAI-selected and Ollama-selected workflow fakes with identical
application semantics; one authority build/workflow/lower execution per call;
fresh deterministic attempt identity; lower request/provider/envelope/output
lineage; completed/success/single ordinal-zero output requirements; timeout,
cancellation, provider/internal/partial/malformed mappings; exact unmodified
generated text; one exact `model_validate_json(..., strict=True)` call; zero
explicit `json.loads`; empty/nonempty/nested tuple-array compatibility; safely
distinguished malformed JSON and schema-invalid JSON; exact validated-model
return; zero preprocessing/repair/fallback/retry/cleanup/persistence/Producer;
copy/deepcopy/pickle/repr/error-graph safety; passive imports/construction; and
frozen integrity. Its dependency/import tests explicitly reject every
coordinator-level type listed in section 8.

Revision 3C.1 specifically tests the exact five-file runtime package and
focused test; exact three-symbol exports and order; absence of configuration
error aliases and public controlled-generator factories; exact session-factory
constructor/open signatures; exact session properties and identity returns;
the recorder identity shared with the adapter without adapter traversal;
operation-reference binding; open/closed behavior and access-after-close;
explicit prohibition of context management; identity copy/deepcopy and rejected
pickle; explicit OpenAI and Ollama fake composition with the unselected path
untouched; no default/alias/discovery/fallback; zero execution/generation on
construction and property access; byte-for-byte runtime-fingerprint parity with
the frozen constructor across provider/model/reference, Unicode, and tagged
numeric/timeout types, plus forbidden-private-import scanning; contiguous
immutable recorder snapshots;
exactly-once close and deterministic second-close failure; reverse-order
partial-construction cleanup without closing injected dependencies; malformed
dependency descriptors and dynamic hooks; error/traceback isolation; passive
fresh-process import/factory construction; and frozen integrity.

## 19. Hard gates

### Gate A — generation options: **RESOLVED BY CLOSED POLICY**

Temperature, maximum tokens, model and timeout are bound to the runtime session
and request fingerprint. Top-p accepts only exact neutral value 1, seed only
null, stops only empty, structured mode only true. Anything else fails before
composition. Implementation MUST prove atomic session/options authority.

### Gate B — deterministic artifacts: **RESOLVED**

All artifacts have existing deterministic constructors and the exact order in
section 6. No AI artifact is invented.

### Gate C — operational result: **RESOLVED**

Section 12 is exact and closed.

### Gate D — retry/timeout/cancellation: **RESOLVED**

Section 9 follows actual `ControlledGenerator` behavior and assigns singular
ownership.

### Gate E — structured equivalence: **RESOLVED BY APPLICATION ENFORCEMENT**

Both providers receive identical prompt/schema semantics; strict application
JSON-mode validation is identical. Frozen tuple fields accept corresponding
JSON arrays without model changes, preprocessing, or non-strict coercion.
Native schema mode is not claimed. Unsupported policy fails closed.

### Gate F — adapter/execution-request separation: **RESOLVED**

Revision 3C has every input required to build
`EditorGenerationApplicationRequestV1`: exact prompt, schema class, generation
config, provider/runtime authority, clock, cancellation source, reference
factory, attempt recorder, and public fingerprint authority. Its exact
package-private builder accepts no fingerprint input and performs assembly. It
requires no coordinator artifact. One adapter
call maps to one application request and one lower execution. One direct strict
JSON-mode validation call owns exactly one internal parse and one schema
validation; the adapter performs no explicit parse. All adapter references to
`EditorGenerationExecutionRequestV1` are prohibitions or coordinator-boundary
clarifications only.

Repository inspection proves atomic runtime authority is implementable through
section 4.6 using only verified public composition and executor boundaries. The
OpenAI lifecycle remains with its verified composition while its same verified
SDK client is injected into the option-complete verified executor; Ollama has
one explicitly owned client handle. Future runtime-session composition MUST
reproduce this proof with offline fakes and fail closed if exact identity or
cleanup ownership differs; Revision 3C only receives injected authorities and
does not construct either runtime.

### Gate G — strict JSON-mode compatibility: **RESOLVED**

Direct verification against every frozen component output model proves that
`model_validate_json(model.model_dump_json(), strict=True)` returns the exact
model type. `CallToActionGenerationResult` accepts empty and nonempty JSON
arrays for tuple fields. `StoryGenerationResult` accepts nested arrays for its
tuple of `CommentaryBlockResult` values and each block's tuple fields. The
Transition, Opening, Closing, and Call-to-Action models likewise accept their
tuple arrays. Invalid tuple elements remain strict schema errors, a wrong root
remains a model error, and malformed syntax produces `json_invalid`. No frozen
model change, manual conversion, preprocessing, or non-strict validation is
required. Revision 3C is implementation-ready only with this single path.

## 20. Implementation roadmap

### Revision 3B — generation authority and execution-request contract

- Entry: this specification independently implementation-ready.
- Verified output: `editor_generation_authority_v1`, the exact
  `EditorGenerationExecutionRequestV1` aggregate in
  `editor_generation_execution_v1`, and focused tests.
- Forbidden: execution, providers, Editor generation, Revision 2 changes.
- Exit: exact options/schema/application-request identity and coordinator-level
  deterministic execution-request authority, object/passivity tests, full
  gates, independent verification.
- Rollback: remove additive files/tests.
- Commit/tag: only after verification and separate Git authorization.

### Revision 3C — neutral language-provider adapter

- Entry: verified 3B; independently verified and tagged Revision 3B.1 public
  fingerprint authority; and frozen implementation-ready Execution
  Specification V3.
- Authorized: `editor_generation_provider_adapter_v1` files and focused test.
- Forbidden: coordinator, CLI, persistence, Producer, provider modifications.
- Exit: exact prompt/schema/options, fake OpenAI/Ollama equivalence, direct
  strict JSON-mode validation with frozen tuple compatibility,
  timeout/cancellation cardinality, exact package-private application
  request construction through the public fingerprint authority, full gates,
  independent verification.
- Rollback/Git policy: additive removal; no Git action without authorization.

### Revision 3C.1 — runtime session and factory

- Entry: verified 3C and this independently implementation-ready Runtime
  Specification V2 boundary.
- Authorized files only:
  `editor_generation_runtime_v1/__init__.py`, `composition.py`, `errors.py`,
  `models.py`, `protocols.py`, and
  `tests/test_editor_generation_runtime_v1.py`.
- Forbidden: `session.py`, `factory.py`, Revision 3D, generation execution,
  CLI, persistence, Producer, provider modification, discovery, routing, and
  fallback.
- Exit: exact public API/session surface, explicit selected-provider fake
  composition, shared recorder identity, atomic construction, singular cleanup,
  object/passivity/error-isolation tests, full gates, and independent
  verification.
- Rollback/Git policy: additive removal; commit/tag only after verification and
  separate authorization.

### Revision 3D — operational execution coordinator/result

- Entry: verified 3C and verified/tagged Revision 3C.1 runtime session; exact
  coordinator API, deterministic artifact sources, operational result, and
  retry/timeout/cancellation mapping independently confirmed.
- Authorized: `editor_operational_execution_v1` files and focused test.
- Forbidden: Revision 2 changes, CLI, persistence, Producer, provider changes.
- Exit: exact generator call/result/lifecycle/cleanup, complete offline path,
  full gates, independent verification.
- Rollback/Git policy: additive removal; commit/tag only after verification and
  authorization.

### Later revision — CLI rollout

CLI remains outside Revision 3 generation foundation. It requires a separate
specification and verified 3D baseline. Its caller will explicitly compose the
preparation result, execution request, execution coordinator, provider/runtime,
and output/export policy. No file or behavior is authorized here.
