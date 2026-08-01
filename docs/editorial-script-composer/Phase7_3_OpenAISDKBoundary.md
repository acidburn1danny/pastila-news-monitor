# Module 2.9 Phase 7.3 Revision 6 — Explicit In-Process Trust Boundary

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

The official `openai` 2.x package is a declared project dependency. The operational
boundary targets its synchronous Responses API `responses.create` surface and
imports only official exception types for trusted classification. Importing this
isolated package loads SDK definitions but constructs no SDK client. Existing
verified lower-level packages remain importable without loading the SDK.

## Injected capability and dispatch status

`OpenAISDKCapabilityV2` is an immutable nominal wrapper supplied by trusted runtime
composition. Construction validates an explicit exact built-in `max_retries=0`
policy and statically pins the raw `create` function and receiver without descriptor
binding or execution. `complete()` performs exactly one adapter-level invocation
of that pinned capability, with no application retry, fallback, polling, recursion,
or secondary API surface. It does not claim exactly one SDK-internal or network
transport attempt.

Official SDK construction remains the next trusted-composition responsibility.
That layer must construct the official client with `max_retries=0` and inject its
synchronous Responses capability. The adapter neither reads arbitrary SDK private
internals nor independently proves transport retry behavior.

## In-process trust boundary

Application composition and project-owned production modules are trusted, as is
the official SDK capability they inject under ordinary Python runtime behavior.
Provider requests, copied-invalid DTOs, provider responses, exception payloads,
and external provider behavior are untrusted and validated at this boundary.

Malicious code already executing in the same interpreter is out of scope. Importing
and mutating private module state, `object.__new__` or `object.__setattr__` attacks,
monkeypatching project internals, debugger access, and memory instrumentation are
equivalent to in-process code-execution compromise. Python private names, frozen
dataclasses, closures, and sentinels are not security seals against that threat.
Production contains no authority registry and no test transport, response holder,
failure holder, call history, or attempt counter.

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

Operational dispatch sends ordered role/content inputs and preserves model,
temperature, maximum output tokens, and fractional timeout. It explicitly sends
`store=False`, `stream=False`, and `background=False`. The Responses API create
surface does not support stop sequences, so a nonempty stop tuple is rejected
before dispatch rather than silently dropped. No instructions, tools, metadata,
hidden messages, or request headers are added.

The untrusted SDK response is reduced immediately to plain field values. Only
message items containing `output_text` fragments are accepted; tool calls,
refusals, image/audio items, missing text, whitespace-only text, and unknown states
are rejected. Text fragments become separate ordered outputs without concatenation.
Raw SDK models, output items, transports, headers, and clients are never retained.
The structured `created_at` response timestamp is the sole time authority; absence
or invalidity is rejected, and no current clock is read. Unix zero and negative
timestamps are permitted; non-finite, nonnumeric, boolean, overflow, and
platform-invalid timestamps are rejected behind the fixed response error.

## Exceptions, timeout, cancellation, and retries

Exception classification uses trusted official SDK types, structured official
status codes, and built-in timeout authority, never exception text. Authentication,
rate limiting, timeout, invalid request, provider unavailability, and unknown internal errors map to stable
`OpenAIClientErrorCategoryV2` values. Malformed responses are represented by the
dedicated reconstruction error boundary.

Timeout is declarative and copied unchanged into the SDK request specification.
No timer, sleep, or deadline is created. Cancellation remains exclusively the
verified executor's pre-dispatch check; this boundary claims no mid-flight
cancellation.

Normal `completed` state maps to `stop`. Structured `incomplete` reasons
`max_output_tokens` and `content_filter` map to `length` and `content_filter`.
Completed responses require absent incomplete details and completed message items.
Incomplete responses require matching incomplete message items and exactly one of
the two supported reasons. Failed, cancelled, queued, in-progress, mixed, padded,
case-altered, and otherwise contradictory states are rejected. SDK exceptions are
translated using trusted official SDK exception types and structured status codes.
Classification and request-bearing execution occur in private frames that return
only a safe result or immutable failure token. Those frames exit before a separate
clean helper raises the public fixed error; the public traceback contains no
request, arguments, prompt, raw exception, body, headers, or transport in adapter
locals. Context and cause are also absent. Python tracebacks expose module globals;
the adapter therefore guarantees that its globals hold no request-specific,
response-specific, credential, or raw-exception state.

Temperature is forwarded exactly when supplied. Model-specific temperature support
is provider-owned; a structured provider rejection maps to invalid request and
does not trigger retry, fallback, or model substitution.

## Credential and operational exclusions

Credentials and official SDK construction belong to the next runtime-composition
revision. This adapter has no API-key parameter, environment or `.env` access,
automatic SDK construction, streaming, async execution, persistence, logging,
telemetry, registration, or composition change. Cancellation remains the verified
outer executor's pre-dispatch responsibility; no mid-flight cancellation is
claimed. Tests use injected offline capabilities only, and no live request is made
during this revision.
