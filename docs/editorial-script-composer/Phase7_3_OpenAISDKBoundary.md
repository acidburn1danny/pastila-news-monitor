# Module 2.9 Phase 7.3 Revision 2 — OpenAI SDK Boundary

Status: Implemented — awaiting independent verification

## Boundary and dependency direction

The isolated dependency direction is:

```text
provider_v2
    ↑
provider_execution_v2
    ↑
provider_execution_openai_v2
    ↑
provider_execution_openai_sdk_v2
    ↑
future runtime composition
```

The official `openai` package is already a declared project dependency, but this
revision deliberately imports no SDK module. Existing verified packages therefore
remain importable without loading the SDK. Missing or deferred SDK dispatch is
reported locally through `OpenAISDKDependencyError`.

## Injected capability and dispatch status

`OpenAISDKClientV2` requires an already-authorized `OpenAISDKCapabilityV2`. The
protocol exposes only one future `create(OpenAISDKRequestV2)` operation. The client
does not construct `OpenAI()`, discover endpoints, read credentials, or use global
state. Constructor validation is static and does not bind descriptors or invoke the
capability.

Revision 1 intentionally leaves `complete()` non-operational and raises a
deterministic dependency error. It performs no live call and never fabricates a
successful provider response. Revision 2 will connect the pure mapping and
reconstruction boundaries to exactly one invocation of the injected capability.

## Pure request and response boundaries

`build_openai_sdk_request` defensively reconstructs the verified execution request
and produces immutable SDK call data containing only the model, ordered messages,
timeout, temperature, output-token limit, and stop sequences. Credentials,
headers, endpoints, transport configuration, retry policy, and mutable dictionaries
are absent.

The exported SDK request DTO also enforces these invariants autonomously. Model
identifiers are strict, nonblank, and unpadded. Message content is an exact string
and must contain non-whitespace text while preserving meaningful leading or
trailing whitespace exactly, matching the verified OpenAI request policy. Stop
sequences are copied into tuples and must be exact, nonblank, unpadded, unique
strings in caller order. No value is trimmed, normalized, repaired, or dropped.

`reconstruct_openai_sdk_response` retains only response ID, model, completion time,
ordered text outputs, and recognized finish reasons. Raw SDK models, HTTP objects,
headers, and transport internals are discarded. `stop`, `length`, and
`content_filter` are mapped explicitly; missing fields, duplicate positions,
copied-invalid nested values, and unknown finish reasons fail deterministically.
Output text must be an exact nonempty string containing non-whitespace text;
meaningful surrounding whitespace is preserved exactly. Whitespace-only text is
rejected before it can establish provider authority. Defensive reconstruction
revalidates copied Pydantic instances and every nested output rather than trusting
their runtime types.

## Exceptions, timeout, cancellation, and retries

Exception classification uses structured status codes and built-in timeout type,
never exception text. Authentication, rate limiting, timeout, cancellation,
invalid request, provider unavailability, and unknown internal errors map to stable
`OpenAIClientErrorCategoryV2` values. Malformed responses are represented by the
dedicated reconstruction error boundary.

Timeout is declarative and copied unchanged into the SDK request specification.
No timer, sleep, or deadline is created. Cancellation remains exclusively the
verified executor's pre-dispatch check; this boundary claims no mid-flight
cancellation.

The official SDK may retry by default. Revision 2 runtime construction must set
`max_retries=0` on the injected official SDK client before enabling dispatch. The
application client will make one capability call and implement no retry, fallback,
or recursion.

## Credential and operational exclusions

Credentials belong to future runtime composition. This revision has no API-key
parameter, environment or `.env` access, SDK client construction, live request,
streaming, async execution, persistence, logging, telemetry, registration, or
composition change.

Revision 2 adds semantic DTO hardening only. It does not add operational SDK
execution or change the deferred responsibilities of the future dispatch
successor.
