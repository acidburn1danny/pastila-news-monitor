# Module 2.9 Phase 7.2 Revision 1 — Provider Execution Boundary

**Status: IMPLEMENTED — AWAITING INDEPENDENT VERIFICATION**

## Revision 2 authority and scalar corrections

Revision 2 introduced intrinsic descriptor validation and strict scalar policies.
Revision 3 supersedes its envelope-derived intent projection with the independent
request-intent authority described below.

Execution metadata preserves caller order and is stored as immutable tuples.
Keys and values must be strict strings and must contain non-whitespace text;
duplicate keys are rejected. Mutable input collections are copied during model
construction. Timeout values must be strict positive finite integers or floats;
booleans, strings, NaN, and infinities are rejected. Execution identifiers and
failure codes are strict, unpadded, non-whitespace strings. Execution outcomes
must be supplied as `ExecutionOutcomeV2` instances; raw strings are not coerced.

These corrections introduce no execution implementation or operational
capability. The frozen Phase 7.1 production baseline remains unchanged.

## Revision 3 independent authority and nested revalidation

`ProviderExecutionRequestV2` requires an independently supplied frozen
`ProviderRequestIntentV2`. Authoritative intent is never derived from the request
envelope. Validation strictly reconstructs the descriptor, request intent,
request envelope, execution context (including cancellation), and timeout policy
before using their values. The frozen descriptor validator runs first, followed
by frozen request-envelope validation against the independently supplied intent
and selected descriptor; explicit descriptor and adapter lineage checks follow.

Consequently, a correctly resealed envelope with altered request-intent fields is
rejected against the unchanged authoritative intent. Copied Pydantic instances
are not trusted merely because their runtime type matches: accepted nested
contracts are safe reconstructed equivalents, while the caller's inputs remain
unchanged. Result projections are likewise strictly reconstructed at the result
boundary. Validation failures use stable categories and do not expose artifact
representations.

`CancellationTokenV2.cancellation_requested` accepts only exact `True` or
`False`; strings, numbers, nulls, and custom truthy objects are rejected without
coercion. Revision 3 adds no executor, provider behavior, transport, SDK,
networking, persistence, or operational capability. Phase 7.1 remains frozen.

## Architectural goal

Phase 7.2 Revision 1 defines the provider-neutral contract between the frozen
provider registry and future execution implementations. It introduces no provider
execution. Its only purpose is to make future execution substitutable, explicit,
and isolated from Phase 7.1.

The dependency direction is:

```text
provider_v2 (FROZEN)
        ↑
provider_execution_v2
        ↑
future execution adapters
```

`provider_execution_v2` may consume frozen provider descriptors, request
envelopes, and result projections. The frozen provider core does not import or
discover the execution package.

## Responsibilities

### Execution request

`ProviderExecutionRequestV2` binds:

- the selected frozen `ProviderDescriptorV2`;
- the independent authoritative `ProviderRequestIntentV2`;
- the authoritative `ProviderRequestEnvelopeV2`;
- immutable `ExecutionContextV2` runtime metadata;
- a declarative `TimeoutPolicyV2`.

The request validates provider, descriptor, and adapter lineage. It contains no
transport, HTTP, authentication, SDK, or credential fields.

### Execution context

`ExecutionContextV2` carries an externally supplied request identifier, an aware
request timestamp, an immutable cancellation-state snapshot, and immutable string
metadata. It performs no logging, telemetry, cancellation, clock, or timer work.

### Cancellation and timeout

`CancellationTokenV2` describes whether cancellation has been requested. It does
not implement threading, events, callbacks, or cooperative cancellation.

`TimeoutPolicyV2` describes a positive timeout budget in seconds. It does not
create timers or use synchronous or asynchronous scheduling.

### Execution result

`ProviderExecutionResultV2` represents exactly one execution-layer outcome:

- `completed`;
- `provider_failure`;
- `timeout`;
- `cancelled`;
- `internal_execution_failure`.

A completed execution carries the existing frozen
`ProviderResultProjectionV2`. Other outcomes carry neutral failure details and no
provider result. This boundary does not duplicate or redefine Revision 3 result
envelopes or provider-result semantics.

### Execution errors

The neutral hierarchy is rooted at `ProviderExecutionBoundaryError` and includes:

- `ExecutionTimeoutError`;
- `ExecutionCancelledError`;
- `ProviderExecutionError`;
- `InternalExecutionError`;
- `ExecutionConfigurationError`.

It contains no provider-specific subclasses.

### Execution protocol

`ProviderExecutorV2` defines one future operation:

```text
execute(ProviderExecutionRequestV2) -> ProviderExecutionResultV2
```

It is a protocol only. Phase 7.2 Revision 1 supplies no implementation, fake,
dispatcher, orchestrator, or runtime binding.

## Separation from frozen Phase 7.1

Phase 7.1 retains exclusive ownership of provider discovery, descriptor and
lifecycle validation, authority, immutable registry composition, and provider
ordering. The frozen registry gains no `execute`, `run`, `invoke`, `request`,
`response`, `transport`, or `client` operation.

The 15 frozen Phase 7.1 files and their hashes remain exactly those recorded in
`Phase7_1_Revision8_Integrity.md`.

## Explicit non-goals

This revision does not implement:

- provider or fake-provider execution;
- HTTP or any other transport;
- `requests`, `httpx`, `aiohttp`, or `asyncio` behavior;
- OpenAI, Claude, Gemini, Ollama, or other SDK integration;
- credentials, environment variables, API keys, or authentication;
- retries, fallback, rate limiting, or backoff;
- streaming or response parsing;
- logging, tracing, metrics, or telemetry;
- persistence, caching, databases, or filesystem output;
- clocks, timers, scheduling, or cancellation mechanisms;
- runtime provider discovery or automatic registration.

## Future revisions

Revision 2 may introduce deterministic fake execution for contract verification.
Real provider implementations, SDK adapters, network policy, retries, streaming,
and operational concerns require separately reviewed later revisions. None are
authorized by this boundary specification.

## Revision 5 reference

The provider-neutral contracts remain unchanged. The specification-only OpenAI
mapping boundary built above this layer is documented in
`Phase7_2_OpenAIExecutionBoundary.md`; it contains no executor, SDK, or networking.
