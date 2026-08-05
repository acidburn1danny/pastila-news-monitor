# Phase 4.2 — Editor Generation Execution Specification V1

Status: **normative specification — ready for independent implementation-readiness review**

Baseline: `phase-4.2-editor-operational-r2-verified` / `d25ac84bdae8667ff5331de19516002412c4eea3`

## 1. Normative scope

The words **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, and **MAY** are
normative. This document specifies additive future work only. It changes no
frozen contract or implementation.

The future flow is exactly:

```text
EditorOperationalPreparationResultV1
  -> EditorGenerationPreparationCoordinatorV1
  -> EditorGenerationExecutionRequestV1
  -> EditorOperationalExecutionCoordinatorV1
  -> ControlledGenerator
  -> EditorNeutralLanguageModelProviderV1
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
  -> existing LanguageModelProvider/GenerationPrompt and frozen Scout workflow API

editor_generation_runtime_v1
  -> verified public OpenAI/Ollama composition and Scout workflow APIs
```

The authority package imports no Editor domain type. The adapter imports no
provider implementation, SDK, deterministic builder, coordinator, CLI,
persistence, or Producer type. Frozen packages never import these packages.

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
) -> None: ...

def open(
    self,
    options: EditorGenerationRuntimeOptionsV1,
) -> EditorGenerationRuntimeSessionV1: ...
```

It branches exactly once on the exact `ProviderChoiceV1`; this is composition,
not routing. It opens only the selected provider. The unselected composer or
factory is not invoked. It creates exactly one `ProviderSelectorV1`, registers
exactly one selected executor, creates the frozen workflow/bridge composition,
mints the runtime authority atomically, then creates the adapter. Composition
failure closes any acquired selected resource exactly once before returning the
fixed `Editor generation runtime composition failed.` error.

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
`EditorNeutralLanguageModelProviderV1`, and the selected lifecycle authority.
Its public read-only properties are `workflow`, `runtime_authority`, and
`adapter`. `close() -> None` invokes the lifecycle authority once; a second call
raises fixed `Editor generation runtime session is already closed.` without a
second lower close. A closed session cannot expose usable dependencies. It is
identity-only, address-free in repr, copy/deepcopy return identity, and pickle
is rejected.

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
option. Structured enforcement is application-owned strict parsing.

OpenAI and Ollama receive the identical single generation message. Neither
receives a native schema option. If future policy requires native provider
schema enforcement, both paths fail closed until the neutral contract and both
verified providers support it; no provider-specific editorial branch is allowed.

## 6. Deterministic enrichment and execution request

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
5. construct `EditorGenerationApplicationRequestV1` using `prompt.text` exactly;
6. build one `ProviderExecutionRequestV2` through the new authority;
7. wrap it in `ScoutRuntimeRequestV1(True, lower_request)`;
8. call `workflow.execute_provider_neutral` exactly once;
9. reconstruct `ScoutRuntimeResultV1` and validate request/provider/envelope and
   output source-reference lineage;
10. record one safe attempt observation;
11. require completed execution, successful provider result, exactly one output,
    ordinal zero, and completed finish reason;
12. copy `generated_text` exactly; reject empty, leading/trailing whitespace, or
    any text not exactly one JSON document;
13. parse once with `json.loads` and duplicate-key rejection; require exact dict;
14. call `output_schema.model_validate(parsed, strict=True)` exactly once; and
15. return that validated model.

No trim, normalization after authority, Markdown handling, fence stripping,
repair, coercion, retry, fallback, second parse, or provider branch is permitted.
Malformed JSON/schema maps to fixed `ProviderStructuredOutputError("Provider
returned invalid structured output.")` from no cause. Provider failure maps to
the existing safe Provider error class. Timeout maps to `ProviderTimeoutError`,
cancellation to a new non-timeout `ProviderCancellationError` subclass of
`ProviderError`, and malformed/lineage/internal failures to fixed safe provider
errors. Raw lower messages are never retained.

### 8.2 Attempt observation

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

`EditorOperationalExecutionCoordinatorV1` is separate from Revision 2.

Constructor:

```python
def __init__(
    self,
    *,
    session_factory: EditorGenerationRuntimeSessionFactoryV1,
    generator_factory: EditorControlledGeneratorFactoryV1,
) -> None: ...
```

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
2. create one runtime session for exact request options/provider;
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
(
    "EditorGenerationExecutionRequestV1",
    "EditorGenerationPreparationCoordinatorV1",
    "EditorGenerationPreparationError",
)
```

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

class EditorControlledGeneratorFactoryV1(Protocol):
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
    def create(self) -> EditorAdapterDependenciesV1: ...
```

`EditorOllamaRuntimeHandleV1` contains exact private executor and lifecycle
authorities and exposes neither publicly. `EditorAdapterDependenciesV1` is a
frozen private bundle containing exactly one clock, cancellation source,
reference factory, and recorder. Its factory returns fresh operation-scoped
dependencies; no dependency is global or shared between sessions.

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
13. exact successful text extraction, duplicate-key rejection, no trim/fence or
    repair, one JSON parse, strict Pydantic validation;
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
parsing is identical. Native schema mode is not claimed. Unsupported policy
fails closed.

Repository inspection proves atomic runtime authority is implementable through
section 4.6 using only verified public composition and executor boundaries. The
OpenAI lifecycle remains with its verified composition while its same verified
SDK client is injected into the option-complete verified executor; Ollama has
one explicitly owned client handle. Revision 3B MUST reproduce this proof with
offline fakes and fail closed if exact identity or cleanup ownership differs.

## 20. Implementation roadmap

### Revision 3B — authority and runtime-binding contracts

- Entry: this specification independently implementation-ready.
- Authorized: `editor_generation_authority_v1` and
  `editor_generation_runtime_v1` files plus focused tests only.
- Forbidden: execution, providers, Editor generation, Revision 2 changes.
- Exit: exact options/schema/request identity, atomic binding proof with fake
  sessions, object/passivity tests, full gates, independent verification.
- Rollback: remove additive files/tests.
- Commit/tag: only after verification and separate Git authorization.

### Revision 3C — deterministic enrichment request

- Entry: verified 3B.
- Authorized: `editor_generation_execution_v1` files and focused test.
- Forbidden: provider/generation execution, Revision 2 changes.
- Exit: exact four-builder order/artifacts/request lineage, zero AI, full gates,
  independent verification.
- Rollback and commit/tag policy: additive removal; Git only after verification
  and authorization.

### Revision 3D — neutral language-provider adapter

- Entry: verified 3B–3C and atomic verified runtime session composition.
- Authorized: `editor_generation_provider_adapter_v1` files and focused test.
- Forbidden: coordinator, CLI, persistence, Producer, provider modifications.
- Exit: exact prompt/schema/options, fake OpenAI/Ollama equivalence, result
  parsing, timeout/cancellation cardinality, full gates, independent verification.
- Rollback/Git policy: additive removal; no Git action without authorization.

### Revision 3E — operational execution coordinator/result

- Entry: verified 3D.
- Authorized: `editor_operational_execution_v1` files and focused test.
- Forbidden: Revision 2 changes, CLI, persistence, Producer, provider changes.
- Exit: exact generator call/result/lifecycle/cleanup, complete offline path,
  full gates, independent verification.
- Rollback/Git policy: additive removal; commit/tag only after verification and
  authorization.

### Revision 3F — CLI rollout

CLI remains outside Revision 3 generation foundation. It requires a separate
specification and verified 3E baseline. No file or behavior is authorized here.
