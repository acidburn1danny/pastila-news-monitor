# Phase 4.2 — Editor Generation Execution Specification V6

Status: **normative specification — singular runtime-composition ownership and workflow-factory lifecycle corrected**

Baseline: `phase-4.2-editor-generation-runtime-spec-v2-ready` / `612f68345ded9ed23e9ff866f41b318d49ce810a`

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
    legacy_workflow: LegacyScoutWorkflowExecutionV1,
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
factory is not invoked. It creates exactly one operational selected executor
and one package-private inert executor for the unselected identity, registers
exactly `openai` and `ollama`, creates exactly one frozen `ProviderSelectorV1`,
selects only the explicit provider, constructs the authoritative
`ScoutRuntimeCompositionV1`, constructs one package-private workflow factory
that retains the exact legacy dependency, passes the composition identity
exactly once to that factory, mints the runtime authority atomically, then calls
the adapter
dependency factory with the exact coordinator operation reference and creates
the adapter with the exact injected fingerprint authority.
The operation reference is identity input only; no execution request or
deterministic artifact is passed to or retained by the adapter. Composition
failure closes any acquired selected resource exactly once before returning the
fixed `Editor generation runtime composition failed.` error.

Factory construction is inert. It statically validates `legacy_workflow` and
all other injected dependencies, retains their exact identities without copy,
deepcopy, wrapper, registry, or hook invocation, and constructs no private
workflow factory or runtime/provider/session value. It owns no operational
resource. Only explicit `open(options, operation_reference=...)` may construct
the private workflow factory, compose the selected provider, create resources,
create the operation-scoped adapter dependencies and recorder, mint the runtime
authority, create the adapter, and publish the session. `options` is exact
`EditorGenerationRuntimeOptionsV1`; `operation_reference` is an exact built-in,
nonempty, unpadded NFC string of at most 120 characters. Provider selection is
only `options.provider`, with exact `ProviderChoiceV1.OPENAI` or
`ProviderChoiceV1.OLLAMA`; there is no string input, alias, default, case fold,
normalization, discovery, routing, or fallback.

`EditorGenerationRuntimeSessionFactoryV1` is frozen, slotted, init-disabled,
identity-dependency-bearing, and has no `__dict__`, setter, cached workflow
factory, mutable/global hidden state, or public dependency property. Its private
fields retain exactly the five constructor dependency identities, including the
legacy workflow and excluding `_EditorScoutWorkflowFactoryV1`. Its fixed repr
is `EditorGenerationRuntimeSessionFactoryV1(<injected dependencies>)` and calls
no dependency repr. Equality compares exact dependency identities without
calling dependency equality. Shallow copy constructs a new validated public
factory wrapper preserving those same identities; deepcopy does the same
without traversing dependencies. Pickle raises fixed `TypeError("Editor
generation runtime session factory cannot be pickled.")` before traversal.
Every public operation revalidates exact retained fields and static descriptors;
post-construction substitution or copied-invalid state fails with the fixed
runtime-composition error.

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

#### 4.6.1 Selector-compatible unselected registration policy

The frozen `ProviderSelectorV1` requires both supported registrations before it
selects one. Revision 3C.1 therefore uses exactly this deterministic flow:

```text
exact ProviderChoiceV1
  -> construct only its verified operational executor
  -> construct one inert executor carrying the other ProviderChoiceV1
  -> reconstruct registrations in (openai, ollama) order
  -> ProviderSelectorV1(exact config, exact two-registration tuple)
  -> retain only selector.executor for the explicit choice
```

For OpenAI, the tuple is `(openai -> selected verified OpenAI executor, ollama
-> inert ollama executor)`. For Ollama, it is `(openai -> inert openai
executor, ollama -> selected verified Ollama executor)`. Registration order is
always `ProviderChoiceV1.OPENAI`, then `ProviderChoiceV1.OLLAMA`; the selector
input is exactly `tuple[ProviderExecutorRegistrationV1,
ProviderExecutorRegistrationV1]`. The configuration is exactly
`ProviderSelectionConfigV1(provider=options.provider)`. Both registration
instances are reconstructed from their exact public `provider` and `executor`
attributes and must retain identity equality before selector construction.
There is no separate registration fingerprint or provenance field in the
frozen registration contract; provenance is the exact canonical
`ProviderChoiceV1` key, statically validated executor type, and, for the
selected executor, the already specified verified descriptor/configuration
authority. No fingerprint is fabricated.

The session factory is the sole selector and runtime-composition owner. After
selector construction it constructs exactly one `ScoutRuntimeCompositionV1`
from:

```python
ScoutRuntimeCompositionV1(
    selector=selector,
    config=ScoutRuntimeConfigV1("editor-generation-runtime-config-v1"),
    options=ScoutRuntimeOptionsV1("editor-generation-runtime-options-v1"),
    cancellation=ScoutCancellationV1(False),
)
```

The two fixed identities describe only this frozen bridge composition and are
not provider, model, request, or fingerprint authority. The false composition
cancellation value is inert bridge configuration; fresh authoritative request
cancellation remains owned by the adapter/application request and is never
inferred from this value. The session factory reconstructs the candidate
composition exactly once with `copy.copy`, requires a distinct exact
`ScoutRuntimeCompositionV1`, the same selector identity, and exact equality of
reconstructed config, options, and cancellation, then discards the candidate.
The reconstructed object is the sole authoritative application-owned
composition. At `open` stage 10 the session factory constructs one exact
`_EditorScoutWorkflowFactoryV1` with its retained exact legacy-workflow
identity, then passes the authoritative composition exactly once as the sole
argument to
`EditorScoutWorkflowFactoryV1.create`. The create argument is the authoritative
composition by identity. The workflow factory neither copies nor reconstructs
it, and the frozen `ScoutRuntimeExecutionBridgeV1` constructor retains that
exact supplied composition identity. Registrations and inert state are not
copied into runtime authority or runtime-fingerprint semantics;
the selected provider remains exactly `options.provider`, and the existing
runtime fingerprint continues to cover exact options, operation reference, and
selected-provider/model semantics only.

`composition.py` owns the sole concrete package-private primitive:

```python
@dataclass(frozen=True, slots=True, repr=False)
class _NonOperationalProviderExecutorV2:
    provider: ProviderChoiceV1

    def __init__(self, *, provider: ProviderChoiceV1) -> None: ...

    def execute(
        self,
        request: ProviderExecutionRequestV2,
    ) -> ProviderExecutionResultV2: ...
```

The annotations above resolve to the exact frozen classes from
`pastila_scout.provider_execution_v2.models`. `execute` is an ordinary
instance function defined directly on the exact class: no property,
static/class method, partial, wrapper, dynamic hook, instance substitution,
variadic argument, default argument, or forged annotation is permitted. The
class is final by exact-type validation. Its sole retained field is an exact
canonical `ProviderChoiceV1`; construction rejects every other type. OpenAI
inert identity is exactly `ProviderChoiceV1.OPENAI`; Ollama inert identity is
exactly `ProviderChoiceV1.OLLAMA`. It never infers identity from a model, URL,
descriptor, selected executor, or string and never reuses or impersonates the
selected identity.

The inert executor is value-equal only to the same exact class carrying the
same exact provider. Its fixed, address-free representation is
`_NonOperationalProviderExecutorV2(provider='openai')` or
`_NonOperationalProviderExecutorV2(provider='ollama')`. `copy.copy` and
`copy.deepcopy` return the same immutable identity without dependency
traversal. Pickle is rejected by a fixed `TypeError("Non-operational provider
executor cannot be pickled.")` raised before state traversal. Authoritative
reconstruction calls the exact constructor with the retrieved exact provider,
requires equality and exact field parity, and rejects copied-invalid state.
The type is absent from package `__all__`, has no alias, and is not imported by
Revision 3D.

If incorrectly invoked, `execute` first strictly reconstructs
`ProviderExecutionRequestV2` from `request.model_dump(mode="python",
warnings=False)` and requires `request.provider.provider_id ==
self.provider.value`. A wrong request type, malformed/copied-invalid request, or
identity mismatch raises the fixed
`EditorGenerationRuntimeCompositionError("Non-operational provider registration
was invoked incorrectly.")` from no cause or context. For a valid matching
request it returns exactly one freshly reconstructed
`ProviderExecutionResultV2` with:

```text
request_id = request.context.request_id
provider_id = request.provider.provider_id
request_envelope_identity = request.request_envelope.identity
outcome = ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
finished_at = request.context.requested_at
provider_result = None
failure_code = "non-operational-provider-registration"
failure_message = "Non-operational provider registration was invoked."
```

The result is reconstructed through `ProviderExecutionResultV2.model_validate`
with strict input and exact field parity before return. It is non-retryable by
policy: the runtime performs no retry and this fixed code is not classified as
a timeout or retryable selected-provider failure. It is distinguishable from a
genuine selected-provider failure only by that fixed neutral code and message.
It retains no request or exception. Validation errors are discarded, context
and cause are suppressed, and neither the fixed result nor the fixed error,
repr, equality, copy, deepcopy, or pickle path exposes prompt, envelope,
lineage objects, credentials, selected executor, selector, runtime, client,
paths, memory addresses, raw failures, or traceback locals after propagation.

The factory statically validates before selector construction that there are
exactly two exact registration objects in canonical order with distinct exact
keys; the selected key equals `options.provider`; its executor is the exact
verified operational executor type constructed for that provider; the later
application request descriptor has the same canonical `provider_id`; the other
key is the opposite canonical identity and its executor is an exactly
reconstructed `_NonOperationalProviderExecutorV2` carrying that same opposite
identity. It rejects wrong, duplicate, missing, swapped, or selected-as-inert
identities; operational executors under the wrong key; an inert executor under
the selected key; dynamic or forged executor shapes; and copied-invalid
registration or executor state. Validation is static and never invokes an
executor body.

Both registrations satisfy the selector's structural contract, but this does
not create fallback or routing. Cardinality is exactly: registrations 2,
explicit selector constructions 1, explicit selections 1, later selected
executor calls 1, valid-path inert calls 0, fallback attempts 0, and routing
attempts 0. A selected-provider failure is returned unchanged through the
existing path and never invokes the inert executor or other provider.

Construction isolation is exact. OpenAI selection constructs OpenAI operational
resources and one inert Ollama value; it invokes no Ollama factory, HTTP,
transport, model discovery, pull, runtime, or cleanup. Ollama selection
constructs Ollama operational resources and one inert OpenAI value; it invokes
no OpenAI factory, credential/environment read, client, runtime, or cleanup.
The inert value requires no provider-specific configuration and performs zero
credential/environment access, client/provider construction, networking, HTTP,
model loading/discovery/pull, workflow execution, retry, fallback, cleanup,
persistence, filesystem/database access, threads, subprocesses, timers,
stdout/stderr, or warnings. Construction and all object-safety operations are
deterministic local operations only.

The inert executor owns no resource and has no close, aclose, shutdown, or
context-management method. Its cleanup count is always zero. Session close and
partial-construction rollback close only acquired selected-provider lifecycle
authorities. The inert value and its registration are discarded locally and
are never included in rollback ownership.

The corrected atomic `open` algorithm is exactly:

1. validate the explicit provider and all runtime options;
2. construct only the selected operational provider/runtime and retain its
   lifecycle authority;
3. construct and reconstruct the selected registration;
4. construct and reconstruct the opposite-identity inert executor;
5. construct and reconstruct the inert registration;
6. validate and reconstruct both registrations in canonical order;
7. construct `ProviderSelectorV1` with exactly those registrations and exact
   selection config, then require `selector.executor is selected_executor`;
8. construct one candidate `ScoutRuntimeCompositionV1`;
9. authoritatively reconstruct it exactly once, validate identity authority,
   discard the candidate, and retain only the reconstructed composition;
10. construct exactly one `_EditorScoutWorkflowFactoryV1(
    legacy_workflow=retained_legacy_workflow)` after statically revalidating the
    retained identity without invoking its body or hooks;
11. call `workflow_factory.create(
    runtime_composition=authoritative_runtime_composition)` exactly once and
    validate its exact `ScoutWorkflowExecutionV1` result;
12. construct and reconstruct the runtime authority for exactly the selected
    options and operation reference;
13. construct the operation-scoped attempt recorder and remaining adapter
    dependencies;
14. construct the adapter with the exact shared dependencies;
15. construct and validate the runtime session;
16. return the session.

Failure after any stage discards inert local values without cleanup and closes
only already acquired selected lifecycle authorities, exactly once each in
reverse acquisition order. It then raises the existing fixed composition error
from no cause or context. Candidate/authoritative immutable compositions and the
package-private workflow factory are discarded without cleanup. The externally
owned retained legacy workflow, selector, registrations, inert executor,
bridge, and workflow are never closed. No session is published on failure.

Failure timing is exact. A malformed constructor dependency fails during public
session-factory construction with
`EditorGenerationRuntimeCompositionError("Editor generation runtime composition
failed.")`. Valid construction followed by substituted or copied-invalid
retained legacy state fails during `open` stage 10 before a private workflow
factory is published. Private workflow-factory construction failure is also a
stage-10 failure. Bridge, workflow, or workflow-result validation failure is a
stage-11 failure. Every `open` failure uses that same fixed error with
`__cause__ is None`, `__context__ is None`, and suppression true after local/raw
references are discarded. Stage-10 and stage-11 failures close already acquired
selected-provider resources exactly once in reverse acquisition order, close
nothing else, and return no session.

Revision 3D remains provider-blind. It receives only the public runtime session
factory, calls `open`, and consumes the already specified session surface. It
never constructs or inspects registrations, sees the inert executor, accesses
the selector, performs fallback, or interprets selected versus inert status.

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
session and session factory implementation plus the sole package-private
concrete `_NonOperationalProviderExecutorV2`; `models.py` owns only exact
private runtime values; `protocols.py` owns only private injected protocols.

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
observation. Snapshots are immutable ordered tuples with recorder-global,
contiguous attempt numbers starting at one, no duplicates or gaps, and distinct
request references. The exact recorder identity exposed by the opened session
is the sole operation-membership authority. The recorder is bound privately to
the session operation reference, but the safe public observation deliberately
does not duplicate that text and its request reference is opaque. Revision 3D
MUST NOT parse or recompute operation identity from a request reference, require
references to embed operation text, or attempt to detect foreign/mixed
operation-reference text in individual observations.

Property access and snapshot perform no provider execution and create no
attempt. The coordinator accesses the exact session recorder, invokes
`session.attempt_recorder.snapshot()` exactly once from coordinator-owned code
after generation terminates, and never accesses or reads it again.
It invokes `snapshot()` on that exact retrieved identity, preserves order, and
reconstructs observations without recording, mutating, repairing, reordering,
fabricating, or recomputing them. There is no second recorder identity or
private adapter field available for comparison; the coordinator MUST NOT invent
one or attempt to detect substitution that occurred before the authoritative
public property access. Adapter-owned internal recorder snapshots during
provider execution are outside this coordinator-owned cardinality.

The snapshot is operation-global and variable length. After at least one
adapter dispatch its length is a positive integer determined by generated
stories, transitions, opening, closing, conditional CTA, component-semantic
attempts, and timeout retries. It has no global one-observation success rule and
no maximum of two. Zero observations are valid only when a terminal failure
occurs after session open but before the first adapter invocation; after public
evidence that dispatch began, zero observations are invalid provenance.

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

This malformed-versus-schema distinction is adapter-internal only. Both paths
cross the public adapter boundary as `ProviderStructuredOutputError`, are
caught by the frozen `ControlledGenerator`, and are ultimately observable by
Revision 3D only as `ControlledGenerationError`. Their provider attempt is
correctly recorded as `COMPLETED` because lower provider execution completed
before application-owned structured-output acceptance failed. The attempt
record exposes no malformed-versus-schema discriminator.

Revision 3D follows an observable-authority rule: it classifies failures only
from public, verified, reachable contracts at its boundary. It MUST NOT derive
a category from exception text or string matching, raw provider messages, raw
generated text, Pydantic or JSON-parser details, private adapter helpers or
private exception types, traceback locals, `__context__`, `__cause__`,
implementation-specific attributes, or guessed mappings. When internal causes
collapse to one public signal, the operational contract exposes one category.

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
5. access the exact session recorder and invoke
   `session.attempt_recorder.snapshot()` exactly once from coordinator-owned
   code; adapter-owned internal recorder snapshots are outside this
   coordinator cardinality;
6. reconstruct and structurally validate the operation-global provenance;
7. reconstruct `ControlledGenerationResult` and its draft, trace, manifest, and
   final state when generation returned, then cross-validate trace/group order;
8. derive the final observable failure classification from the public terminal
   signal and validated provenance;
9. close the session once;
10. construct/reconstruct `EditorOperationalResultV1` only after the close
   outcome is known; and
11. if an earlier step raises, close once in `finally`, then construct the safe
   failed/cancelled result from the retained candidate state.

The coordinator never publishes a result before cleanup. Cleanup failure after
any opened-session outcome takes publication precedence and maps to
`cleanup_failed`; generated output is suppressed and `cleanup_failed=True`
records the safe fact. The coordinator never attempts a second close.

The coordinator performs no deterministic selection/enrichment, provider
selection policy, raw client access, retry loop, timeout enforcement,
cancellation polling, persistence, CLI, Producer, or output rendering.

When `ControlledGenerator.generate` raises `ControlledGenerationError`, the
coordinator invokes `session.attempt_recorder.snapshot()` exactly once from
coordinator-owned code, validates provenance, and reduces the exact public
exception type to
`controlled_generation_failed` unless a distinct public timeout,
cancellation, provider, invalid-provenance, cleanup, request, or runtime signal
has higher precedence. It closes the runtime session exactly once and publishes
only after successful close. It performs no output reconstruction, second
parse, direct adapter call, coordinator retry, generated-text inspection, or
exception-message inspection. Adapter-owned recorder snapshots used internally
during provider execution are not counted by this coordinator-owned invariant.

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
| `runtime_composition_failed` | `Editor generation runtime composition failed.` | false |
| `provider_failed` | `Editor generation provider failed.` | false |
| `timeout_exhausted` | `Editor generation timed out.` | false |
| `cancelled` | `Editor generation was cancelled.` | false |
| `controlled_generation_failed` | `Editor controlled generation failed.` | false |
| `attempt_provenance_invalid` | `Editor generation attempt provenance is invalid.` | false |
| `controlled_result_invalid` | `Editor controlled generation result is invalid.` | false |
| `internal_execution_failure` | `Editor generation execution failed.` | false |
| `cleanup_failed` | `Editor generation cleanup failed.` | false |

`EditorOperationalGenerationFailureV1` fields are `code`, `safe_message`, and
`retryable=False`. No raw lower code/message is public. Cleanup failure takes
publication precedence over completion and every pre-cleanup terminal failure
because resource ownership did not terminate successfully. It suppresses all
generated output and is retained with `cleanup_failed=True`.

There is no partial draft. Any failed/cancelled outcome has no draft, generation
trace, manifest, or final state and prohibits downstream handoff.

`invalid_execution_request` also covers copied-invalid or inconsistent nested
deterministic artifacts discovered while authoritatively reconstructing the
single frozen execution-request aggregate. The public reconstruction boundary
does not expose which nested artifact failed, so Revision 3D MUST NOT invent a
separate deterministic-artifact failure category.

Because frozen `ControlledGenerator` wraps provider exceptions, terminal
classification is derived only from the operation-scoped safe attempt record
and the exact public exception type, never from exception text or traceback. If
the final observation is cancelled, the result is cancelled. If the final two
immediately consecutive observations have the same prompt fingerprint and both
are timeout, the result is `timeout_exhausted`. A final recorded
`PROVIDER_FAILURE` maps to `provider_failed`. Frozen adapter rejection of a
malformed lower result and frozen adapter rejection of lower lineage both
collapse to the same public internal provider error without a discriminating
attempt observation, are caught by `ControlledGenerator`, and reach Revision 3D
only as `ControlledGenerationError`. Both therefore map to
`controlled_generation_failed`. Revision 3D MUST NOT expose separate
malformed-result, lineage, or hidden-adapter-internal categories.

Every `ControlledGenerationError` with otherwise valid provenance maps to
`controlled_generation_failed` unless a distinct public timeout, cancellation,
provider, invalid-provenance, cleanup, invalid-request, or runtime-session
signal has higher precedence. A final `COMPLETED` observation does not prove
that it belongs to the failing component: it may belong to an earlier completed
component when the later adapter invocation failed before recording. Revision
3D therefore MUST NOT infer structured-output rejection from `COMPLETED`,
attempt position, exception text, or any private diagnostic.

`controlled_generation_failed` uses the generation-failure lifecycle ending in
`failed`; retryable is exact false; draft, trace, manifest, and final state are
absent; downstream handoff is prohibited; valid ordered attempt observations
are retained without rewriting their outcomes; and publication occurs only
after successful runtime-session close. Adapter-internal malformed JSON and
schema-validation distinctions remain private and deliberately collapse into
this same operational category. Internal failure is limited to the two finite
package-owned sources defined next.

`internal_execution_failure` is reserved for an independently observable
coordinator-owned or runtime-owned internal boundary that does not arrive as
`ControlledGenerationError`. Its exhaustive sources are exactly: (A) an
unexpected exception raised by package-owned Revision 3D coordinator code after
dependency validation and entry into a package-owned operation, after neutral
reduction, when no other closed public category applies; and (B) failure to
construct or authoritatively reconstruct `EditorOperationalResultV1` solely
because of package-owned internal corruption, excluding copied-invalid caller
input, malformed provider/generator output, invalid provenance, cleanup failure,
or another existing closed code. Frozen inspection identifies no distinct
public runtime-internal exception/outcome reaching Revision 3D directly, so no
third runtime-signal source exists.

The exclusion list is exhaustive: `internal_execution_failure` never owns a
`ControlledGenerationError`, malformed JSON, schema-invalid output,
structured-output rejection, malformed lower result, lower-lineage rejection,
retry failure before `_record()`, hidden adapter failure, provider failure,
timeout, cancellation, invalid provenance, runtime-session open failure,
cleanup failure, invalid execution request, `controlled_result_invalid`, a
cause inferred from text/private state, a discarded lower cause, or any future
unenumerated signal. A collapsed lower cause is never re-expanded into a more
specific operational category.

After a session opens, classification precedence is closed: cleanup failure;
invalid attempt provenance; a separately observable timeout, cancellation, or
provider failure; `controlled_generation_failed` for every remaining
`ControlledGenerationError`; then an independently observable
`internal_execution_failure`. Invalid execution request and runtime-session
open failure terminate before this opened-session precedence applies.

### 11.1 Operation-global attempt provenance

Attempt-provenance validation belongs exclusively to
`EditorOperationalExecutionCoordinatorV1`. It validates the single immutable
snapshot obtained from the exact `session.attempt_recorder` identity. The
coordinator validates only public fields of exact reconstructed
`EditorGenerationAttemptObservationV1` values and never traverses the adapter,
runtime, lower request/result, or reference factory.

Attempt numbers are recorder-global: the adapter reconstructs the existing
snapshot and assigns `len(snapshot) + 1`. A valid nonempty snapshot therefore
has exact built-in positive numbers `1..N` in tuple order, exact observation
types, globally distinct request references, no duplicate complete observation,
and provider IDs equal to the public runtime provider authority. Total `N` is
variable and is not capped at two.

A public dispatch group is one maximal adjacent run with the same
`prompt_fingerprint`. Frozen generation is sequential. A normal dispatch group
contains one observation. A timeout retry group contains exactly two adjacent
observations with the same prompt fingerprint: the first outcome is `TIMEOUT`,
the second has a fresh request reference and the next recorder-global attempt
number. No third observation may share that timeout-retry run. Semantic retries
are separate generator attempts with newly built prompts and are therefore
separate public groups; Revision 3D does not infer their private reason.

For completed generation, trace/group parity uses this exact partition of the
reconstructed public `GenerationTrace.attempts`: a node is provider-backed if
and only if its `provider_identifier` equals the reconstructed execution
request's `provider.value`; those nodes participate, in tuple order, in parity
validation. A node is deterministic-local if and only if its
`provider_identifier == "deterministic-local"` and its `component_type` is
`GenerationComponentType.ASSEMBLY` or
`GenerationComponentType.TELEPROMPTER_FORMATTING`; those nodes are excluded
from parity validation. Any trace node satisfying neither partition, or a
`deterministic-local` node with any other component type, makes the controlled
result invalid. Collapsing each provider-attempt timeout pair to its terminal
observation MUST produce exactly the ordered prompt fingerprints of the
provider-backed trace nodes. This validates the multi-component story,
transition, opening, closing, and conditional-CTA sequence without inventing a
component type in the observation. For terminal failure, no partial trace is
promoted; the final public group is the relevant terminal authority and all
earlier groups must remain structurally valid.

A nonterminal `TIMEOUT` must be followed immediately in the full snapshot by
its same-fingerprint retry. Two adjacent `TIMEOUT` observations in that group
prove `timeout_exhausted`. A terminal singleton `TIMEOUT` accompanying a public
generator failure is not fabricated into timeout exhaustion: the frozen retry
may have failed before recording a second observation, so it maps to
`controlled_generation_failed`. Timeout retry count is the number of valid
same-fingerprint adjacent pairs whose first observation is `TIMEOUT`; it is not
derived from total snapshot length. Earlier successful groups do not alter a
public terminal provider-failure, cancellation, or timeout mapping and are
never treated as proof of a private structured-output cause.

The retry-before-record scenario is normative. Attempt `N` records `TIMEOUT`
with prompt fingerprint `P`; frozen `ControlledGenerator` performs its sole
same-prompt timeout retry; that retry fails before adapter `_record()`; and
Revision 3D receives `ControlledGenerationError` with the snapshot still ending
at the valid timeout observation. If the available operation-global snapshot is
otherwise valid, this maps to `controlled_generation_failed`, not
`timeout_exhausted`, `internal_execution_failure`, or
`attempt_provenance_invalid`. The coordinator does not require/fabricate a
second observation, infer its outcome/lower code, or treat the recorded timeout
as the final operational outcome. Cleanup failure alone may override this
candidate at publication.

The four timeout cases are disjoint: two adjacent recorded same-prompt
`TIMEOUT` observations prove `timeout_exhausted`; a recorded timeout followed
by a recorded successful same-prompt retry continues according to the generator
result; a recorded timeout followed by an unrecorded retry failure and
`ControlledGenerationError` maps to `controlled_generation_failed`; and an
independently malformed/contradictory public timeout sequence maps to
`attempt_provenance_invalid`.

`attempt_provenance_invalid` is used only for publicly detectable provenance
violations: wrong snapshot type; wrong or copied-invalid observation type;
failure to snapshot the exact retrieved recorder; noncontiguous/out-of-order recorder-global
numbers; duplicate complete observations; duplicate request references;
provider mismatch; invalid same-fingerprint grouping; nonterminal timeout
without its adjacent retry; more than one timeout retry in one group; terminal
outcome inconsistent with the derived public outcome; or a successful
controlled result whose collapsed groups do not match its reconstructed trace.
Opaque operation-reference membership is not revalidated from observation
text.

Provenance failure takes precedence over timeout, cancellation, provider,
generic controlled-generation, and successful-result
classification. The session is still closed exactly once. Cleanup failure then
takes publication precedence over provenance failure. If cleanup succeeds, the
failed lifecycle and `attempt_provenance_invalid` are published with no output,
no handoff, retryable false, public attempts `()`, `attempt_count=0`, and
`timeout_retry_count=0`. Malformed observations and the raw snapshot are never
retained or exposed.

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
For `attempt_provenance_invalid`, attempts are exactly `()`, attempt count and
timeout retry count are zero, and no malformed or partially validated
observation is included. Other terminal outcomes retain the exact validated
operation-global snapshot and total count when provenance is valid.

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
        self,
        *,
        runtime_composition: ScoutRuntimeCompositionV1,
    ) -> ScoutWorkflowExecutionV1: ...

class EditorAdapterDependencyFactoryV1(Protocol):
    def create(self, *, operation_reference: str) -> EditorAdapterDependenciesV1: ...
```

`EditorOllamaRuntimeHandleV1` contains exact private executor and lifecycle
authorities and exposes neither publicly. `EditorAdapterDependenciesV1` is a
frozen private bundle containing exactly one clock, cancellation source,
reference factory, and recorder. Its factory returns fresh operation-scoped
dependencies; no dependency is global or shared between sessions.

`EditorScoutWorkflowFactoryV1` is a package-private protocol located only in
`editor_generation_runtime_v1/protocols.py` and absent from `__all__`. Its
`create` member is one ordinary instance method with exactly one keyword-only
parameter named `runtime_composition`, annotated with the exact frozen public
`ScoutRuntimeCompositionV1`, and exact return annotation
`ScoutWorkflowExecutionV1`. It has no default, overload, positional-only or
variadic parameter, `legacy_workflow`, provider, selected-executor, selector,
wrapper, property/cached property, static/class method, partial, or dynamic
replacement. The session factory statically validates the concrete
implementation's exact descriptor without invoking it or any instance hook.

`composition.py` owns exactly one package-private concrete implementation:

```python
@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class _EditorScoutWorkflowFactoryV1:
    _legacy_workflow: LegacyScoutWorkflowExecutionV1

    def __init__(
        self,
        *,
        legacy_workflow: LegacyScoutWorkflowExecutionV1,
    ) -> None: ...

    def create(
        self,
        *,
        runtime_composition: ScoutRuntimeCompositionV1,
    ) -> ScoutWorkflowExecutionV1: ...
```

The constructor requires the exact keyword-only `legacy_workflow` parameter and
statically validates the exact ordinary `execute(self, request:
ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1` protocol shape without invoking
descriptors or bodies. It rejects subclasses, proxies, wrappers, dynamic
attributes, instance method replacement, missing/copied-invalid state, and
every nonconforming signature with the existing fixed runtime-composition
error. It retains the exact dependency identity in its sole private field; no
copy, deepcopy, proxy, registry, lookup, setter, or per-call replacement exists.
Construction performs no workflow/runtime/provider operation.

The implementation is exact-type validated, slotted with no `__dict__`, and
immutable. Its repr is exactly
`_EditorScoutWorkflowFactoryV1(legacy_workflow=<injected>)` and never calls the
dependency repr. Equality is identity only and never calls dependency equality.
`copy.copy` and `copy.deepcopy` return `self` without traversal or resource
duplication. Pickle raises fixed `TypeError("Editor Scout workflow factory
cannot be pickled.")` before state traversal. Every operation revalidates the
retained exact dependency statically and rejects copied-invalid state. It has no
mutable or global hidden state and remains absent from every public export.

`create` first validates by exact type and direct static field inspection that
the supplied object is the sole authoritative `ScoutRuntimeCompositionV1`, its
selector is exact `ProviderSelectorV1`, and its config/options/cancellation are
the exact frozen types with the already specified values. It invokes no
composition descriptor, repr, equality, copy, deepcopy, or reconstruction. It
constructs exactly one `ScoutRuntimeExecutionBridgeV1` from that same supplied
object and requires `runtime_bridge.composition is runtime_composition` and the
bridge's authorized executor identity to be the exact selector executor. The
frozen bridge constructor retains the supplied composition directly and does
not reconstruct it. The factory then constructs exactly one
`ScoutWorkflowExecutionV1(retained_legacy_workflow, runtime_bridge)` and
validates by exact type/direct retained-field identities that the workflow owns
that exact legacy dependency and bridge. It performs no workflow copy or
reconstruction before returning the exact constructed workflow.

The workflow factory performs no provider or executor construction, registration
construction, selector construction or selection, provider inference,
application/runtime-authority construction, execution, fallback, routing,
retry, credential access, networking, or cleanup. It owns no provider resource.
Factory construction additionally performs zero bridge/workflow construction,
legacy execution, attempt recording, JSON validation, persistence,
filesystem/database access, threads, subprocesses, timers, stdout/stderr, or
warnings. `create` may construct only the bridge and workflow and never invokes
either execution method.
Malformed composition, retained legacy dependency, bridge, or workflow
is translated to the existing fixed
`EditorGenerationRuntimeCompositionError("Editor generation runtime composition
failed.")` with cause/context cleared and suppression true after all local and
raw exception references are discarded. It does not close the supplied
composition, selector, executor, legacy dependency, bridge, or workflow.
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
| hidden malformed lower result/lineage | existing recorded attempts only | 0 | `controlled_generation_failed`, no draft | once |
| adapter-internal structured-output rejection | one per existing component attempt | generator policy only | `controlled_generation_failed`, no draft | once |
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
    lineage mismatch, generic controlled-generation failure, internal failure;
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

Revision 3D tests the public operational collapse explicitly. Adapter-internal
malformed JSON and schema-invalid JSON paths both map to
`controlled_generation_failed`; where all public observable inputs are equal,
their public operational results are equal. Each retains the exact lower
`COMPLETED` attempt, exposes no parser/Pydantic detail or generated output,
permits no handoff or coordinator retry, invokes
`session.attempt_recorder.snapshot()` exactly once from coordinator-owned code,
closes the session once, and publishes only after successful cleanup. Tests
MUST prove
that classification never reads exception text or generated text. Every
otherwise unclassified `ControlledGenerationError`, including a later internal
pre-record adapter failure after earlier completed groups, maps to the same
`controlled_generation_failed`. Timeout, cancellation, provider failure,
invalid attempt provenance, cleanup failure, and internal runtime failure remain
distinct only through their public signals.

The same matrix explicitly injects malformed lower-result and lower-lineage
rejection before `_record()` and requires `controlled_generation_failed` with
the same fixed message and materially equivalent public failure object when all
observable inputs match. Earlier valid observations may remain but are not
treated as terminal-cause proof. Tests prohibit lower-result/lineage inspection,
fabricated observations, coordinator retry, and any hidden-adapter mapping to
`internal_execution_failure`; that code is tested only at the independently
observable coordinator/runtime internal boundaries listed in section 11.

The separately named load-bearing requirement
`test_timeout_retry_failure_before_record_maps_to_controlled_generation_failed`
constructs an opened session whose recorder contains one valid `TIMEOUT`
observation for prompt fingerprint `P`, exercises the frozen one retry, makes
that retry fail before adapter `_record()`, and exposes
`ControlledGenerationError` with no second observation. It asserts the result
is `controlled_generation_failed` and is not timeout, internal, or provenance
failure solely because the retry observation is absent; the existing timeout
observation remains unchanged; no observation/lower cause is fabricated; the
coordinator invokes `session.attempt_recorder.snapshot()` exactly once and
closes the session once; adapter-owned internal snapshot calls are not included
in that assertion; output/handoff and coordinator retry are absent; and
separately injected cleanup failure takes precedence.

Companion tests distinguish recorded timeout exhaustion, recorded successful
timeout retry, unrecorded retry failure, and independently invalid timeout
provenance exactly as section 11.1 specifies.

Revision 3D provenance tests additionally cover variable multi-component
snapshots for stories, transitions, opening, closing, CTA present/absent, and
component-semantic attempts; total counts greater than two; exact retrieved
recorder identity and one coordinator-owned snapshot call with no alternate
recorder; wrong snapshot or
observation types; copied-invalid and duplicate observations; duplicate request
references; recorder-global numbering/order; provider mismatch; valid middle
and terminal timeout pairs; nonadjacent retry, repeated timeout retry, and
terminal-group mismatch; provider failure, cancellation, adapter-internal
structured-output rejection, and generic failure after earlier completed
groups; successful exact provider-backed trace fingerprint/group parity with
deterministic-local assembly and teleprompter nodes excluded by the normative
partition; valid zero-attempt pre-dispatch failure; invalid zero
attempts when dispatch is publicly established; empty public attempts/count
zero for `attempt_provenance_invalid`; cleanup precedence; and explicit absence
of operation-reference-text parsing, reference recomputation, mutation, retry,
output, handoff, or malformed-provenance publication.

Revision 3C.1 specifically tests the exact five-file runtime package and
focused test; exact three-symbol exports and order; absence of the inert type,
configuration error aliases, and public controlled-generator factories; exact
session-factory constructor/open signatures; exact session properties and
identity returns; the recorder identity shared with the adapter without adapter
traversal; operation-reference binding; open/closed behavior and
access-after-close; explicit prohibition of context management; identity
copy/deepcopy and rejected pickle; explicit OpenAI and Ollama fake composition;
exactly two registrations keyed in `openai`, `ollama` order; exact selected
verified executor and exact opposite-identity inert executor; frozen-protocol
signature compatibility; passive inert construction; exact fixed inert result
and malformed/wrong-identity fixed error; inert copy/deepcopy/pickle/repr,
copied-invalid, and traceback safety; selected execution once and inert
execution zero; selected failure never invoking inert or fallback; wrong,
swapped, duplicate, missing, and operational-under-wrong-identity registrations
rejected statically without body invocation; OpenAI selection with zero Ollama
operational/network/model activity; Ollama selection with zero OpenAI
operational/credential activity; inert cleanup zero; selected-resource cleanup
only; exact sole selector/registration ownership in the session factory; exact
`ScoutRuntimeCompositionV1` constants and reconstruction; exact workflow-factory
protocol signature with only `runtime_composition`; one candidate composition
construction and exactly one session-factory authoritative reconstruction;
candidate discarded; exact authoritative composition identity passed once;
workflow-factory composition copy/deepcopy/reconstruction counts all zero;
bridge retains that exact identity; exact concrete workflow-factory constructor
retains the legacy workflow once; public session-factory constructor retains
the exact legacy identity but constructs zero private workflow factories and
zero operational values; private workflow factory constructed exactly once at
`open` stage 10 with that retained identity; no cached/preconstructed factory;
stage-10 and stage-11 failure timing plus selected-resource rollback; external
legacy and private factory never closed; exact 16-stage call ordering; create
rejects legacy/provider/executor/selector parameters; public and concrete
factory slots/repr/identity equality/copy/deepcopy/pickle and copied-invalid
safety; one bridge and one workflow constructed with no
workflow reconstruction; no selector, registration, provider, execution, or
cleanup construction by the workflow factory; exact retained legacy-workflow
identity; malformed factory/composition/legacy/bridge/workflow failure isolation;
no duplicate selector or workflow composition; no
default/alias/discovery/fallback/routing;
zero execution/generation on construction and property access; frozen selector
source/hash unchanged;
byte-for-byte runtime-fingerprint parity with
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

### Gate H — selector-compatible isolated composition: **RESOLVED**

Section 4.6.1 supplies both registrations required by the unchanged frozen
selector while constructing only one operational provider. The other canonical
identity is represented by one exact package-private, resource-free, fail-closed
executor. Its invocation result, validation, identity, object safety, passivity,
and cleanup behavior are closed; canonical registration ordering and exact
cardinality prohibit fallback or routing. Revision 3C.1 is implementation-ready
only if its focused tests prove this policy and frozen-selector integrity.

### Gate I — selector/workflow ownership: **RESOLVED**

The session factory alone constructs both registrations, the selector, and the
authoritative `ScoutRuntimeCompositionV1`. The package-private workflow factory
is constructed exactly once during `open` stage 10 from the exact legacy
boundary retained inertly by the public factory; public factory construction
creates no private workflow factory. Its operational `create` method accepts
only the authoritative composition exactly once. It
owns only identity-preserving validation and bridge/workflow construction, and
cannot copy or reconstruct composition or selector state. Runtime authority
remains selected-provider authority and does not include the inert registration.
No second selector, registration, application-owned composition reconstruction,
cleanup owner, fallback, or routing path remains.

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
  Specification V6 workflow-factory lifecycle boundary.
- Authorized files only:
  `editor_generation_runtime_v1/__init__.py`, `composition.py`, `errors.py`,
  `models.py`, `protocols.py`, and
  `tests/test_editor_generation_runtime_v1.py`.
- Forbidden: `session.py`, `factory.py`, Revision 3D, generation execution,
  CLI, persistence, Producer, provider modification, discovery, routing, and
  fallback.
- Exit: exact public API/session surface, explicit selected-provider fake
  composition, canonical two-registration selector input with one selected
  operational and one opposite-identity inert executor, zero unselected-provider
  construction, singular session-factory selector ownership, exact authoritative
  runtime-composition handoff to the package-private workflow factory, singular
  bridge/workflow construction, zero fallback/routing, shared recorder identity,
  atomic construction, selected-resource-only cleanup, inert fail-closed and
  object/passivity/error-isolation tests, frozen-selector integrity, full gates,
  and independent verification.
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
