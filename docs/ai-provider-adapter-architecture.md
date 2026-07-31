# AI Provider Adapter Architecture

The AI Provider Adapter infrastructure sits strictly beneath the frozen
`ControlledRevisionGateway` boundary:

```text
Controlled Revision Runtime
  -> ControlledRevisionGateway
    -> AI Provider Adapter
      -> AI Provider Client
        -> external LLM provider
```

No concrete provider is included in Part 1. Future OpenAI, Gemini, Anthropic,
Azure OpenAI, local-model, and other LLM integrations implement the same adapter
and single-attempt client contracts without changing editorial or corrective
action code.

## Ownership

The adapter owns semantic request and response translation, structured-output
extraction, normalized infrastructure errors, usage accounting, adapter retry
policy, and content-free observability notifications. Prompt projection belongs
only to a future concrete AI Provider Adapter; structured revision intent remains
provider-neutral above this boundary.

The client owns authentication application, SDK or HTTP interaction, connection
handling, cancellation, and enforcement of one transport attempt's timeout. It
does not own semantic mapping or retry policy. The adapter may call the client
again according to its immutable `AIRetryPolicy`; Controlled Revision and all
domain execution remain exactly once.

Credentials are resolved by an injected `AICredentialProvider`. Configuration
contains only an authentication reference and never a credential value. Secrets
must not enter gateway invocations, domain contracts, reports, fingerprints, or
logs.

## Configuration and errors

`AIProviderConfiguration` is immutable and contains provider/model identifiers,
an optional endpoint, authentication reference, timeout, adapter retry and rate
limit policies, structured-output and streaming capabilities, context capacity,
and canonical non-secret metadata.

All concrete provider failures must be normalized into the provider-neutral
taxonomy: authentication, authorization, timeout, rate limit, transport,
malformed response, schema violation, unavailable provider, unsupported
capability, or internal provider failure. SDK exceptions never cross the adapter.

## Composition

`compose_ai_provider_adapter` receives an explicit constructor, configuration,
client, credential provider, and optional observability hook. It constructs once,
retains exact dependency identities in a frozen composition record, performs no
transport, and uses no global registry, singleton, discovery, or import side
effect.

Future integration flow is: compose a concrete client and credential provider,
construct its concrete adapter, inject that adapter as the frozen Controlled
Revision gateway, and compose the existing Controlled Revision execution service.

## Part 2 execution runtime

The canonical runtime accepts the exact `ControlledRevisionInvocation`, validates
immutable configuration, projects exactly one opaque client request, resolves the
external credential once, and coordinates one or more single-attempt client calls.
The same projection is reused for retries. Only the accepted transport response is
interpreted, at most once, into the frozen `ControlledRevisionGatewayResult`.

Retry classification is provider-neutral and policy-owned. Authentication,
authorization, unsupported capability, malformed response, schema violation,
configuration, and projection failures are permanent. Configured timeout, rate
limit, transient transport, and unavailable-provider failures may retry. Backoff
and sleeping are separate injected protocols, so tests never use wall-clock sleep.
Controlled Revision remains one semantic invocation even when transport requires
multiple attempts.

Cancellation is checked before projection and each attempt. The frozen Part 1
client is synchronous and single-attempt; a future concrete client may propagate
cancellation through its own transport implementation. Cancellation stops all
subsequent attempts and produces a normalized result.

Provider exceptions are mapped to safe diagnostic codes. Raw messages, payloads,
credentials, source drafts, instructions, response bodies, and secret references
are excluded from lifecycle events and safe reports. Usage reported by successful
or failed attempts is aggregated outside domain fingerprints. Observability emits
a deterministic, content-free event sequence; hook failures are ignored and do
not alter execution semantics.

`compose_ai_provider_runtime` constructs the runtime from explicit configuration,
client, credential provider, projector, interpreter, exception normalizer, retry
decider, backoff strategy, sleeper, cancellation token, and observer. Composition
performs no projection, credential resolution, transport, or interpretation.

Every future concrete AI Provider Adapter must run the shared behavioral contract
suite proving exact invocation identity, one projection, retry call counts,
permanent-error behavior, exhaustion, cancellation, usage aggregation,
observability ordering, safe deterministic reporting, and absence of fallback.

## Part 2B interpretation and lineage correction

Before the first concrete provider, the internal Part 2 contracts were evolved
directly because there were no external consumers to preserve. No V2 contract
family or parallel runtime was created.

`ProjectedAIProviderRequest` now retains the exact authoritative
`ControlledRevisionInvocation` as well as its fingerprint. The runtime requires
both object identity and fingerprint consistency before credential resolution.
Fingerprint equality proves semantic consistency but cannot prove provenance;
therefore, an equivalent reconstructed invocation is rejected.

The transport client response now contains only opaque raw transport output and
optional transport latency. It does not extract usage, request IDs, model IDs,
completion state, refusals, or structured content. Those semantics belong to the
provider response interpreter.

The interpreter returns one immutable `AIProviderInterpretationResult` containing
the exact frozen gateway result, optional provider-neutral usage, optional provider
request and returned-model identifiers, and canonical safe metadata. The runtime
preserves gateway-result identity, aggregates interpreted usage once, and exposes
only validated infrastructure metadata in safe reports. Requested and returned
model identifiers remain distinct.

Safe metadata is an ordered tuple of unique scalar string pairs. Secret material,
authorization data, source or instruction content, prompts, payloads, response
bodies, raw exceptions, and local paths are rejected. Raw provider responses and
SDK objects have no field in the interpretation contract.

Part 2 fakes now attach the exact invocation and return interpretation results.
Retry, cancellation, backoff, credential, exception, lifecycle, composition, and
safe-report behavior remains otherwise unchanged. This correction makes the
runtime ready for provider-specific response interpretation without moving
semantic parsing into either the client or generic runtime.

## Part 3 OpenAI Controlled Revision adapter

The concrete implementation lives only under `ai_provider_adapter/openai/`.
`projector.py` owns the deterministic Controlled Revision instructions, source
draft projection, authorized scope, preservation requirements, and the strict
output schema. `client.py` owns one synchronous
`client.responses.create(...)` transport attempt. `interpreter.py` owns all
response statuses, refusal and incomplete detection, output extraction, schema
validation, usage, request ID, returned model ID, and gateway-result projection.
`errors.py` maps typed SDK failures to the provider-neutral taxonomy, and
`composition.py` wires those pieces into the existing canonical runtime.

The implementation targets official `openai>=2.48,<3`; it was verified against
2.48.0. Requests use the Responses API with
`text.format.type=json_schema`, a canonical Pydantic-derived schema, and
`strict=true`. Every object schema forbids additional properties and explicitly
requires its declared properties. The requested model is supplied only by
immutable provider configuration; no model registry or fallback exists.

The SDK client is created lazily at the first transport boundary so composition
does not resolve credentials. The canonical runtime resolves the external secret
once per semantic execution. The transport binds one SDK client to that
execution's resolved-credential provider through a weak, execution-scoped entry.
Retries reuse that SDK client and credential; when the execution ends, the weak
entry and authenticated client are released. A later execution resolves its own
credential and constructs its own client, so credential rotation cannot retain a
stale first key. Every SDK client uses `max_retries=0`, and every client call is
exactly one SDK attempt. The configured timeout is forwarded through the official
per-request `timeout` argument. An optional base URL is applied only during SDK
construction.

The client returns the exact raw SDK `Response` object without reading its
content. The interpreter accepts only a completed response with exactly one
completed message and one `output_text` content item. Refusals, incomplete or
unexpected statuses, mixed/conflicting content, malformed JSON, invalid schemas,
and malformed usage fail closed using content-free diagnostic codes. The frozen
gateway result contains only the validated revised `EpisodeDraft` and existing
domain lineage. Request ID (`response._request_id`), returned model, token usage,
latency, and canonical completion metadata remain in infrastructure results and
safe reports, outside domain fingerprints.

OpenAI automatic retries are disabled; retry decisions, backoff, attempts,
aggregation, cancellation checkpoints, lifecycle, and observability remain owned
by the provider-neutral runtime. Synchronous SDK calls cannot be interrupted once
in flight, so cancellation is honored at the runtime checkpoints before
projection, before transport attempts, and before interpretation. No streaming,
tools, persistence, previous-response chaining, provider fallback, model fallback,
or Chat Completions path is present.

Tests use synthetic SDK-shaped responses and injected fake transport only. They
cover deterministic projection and strict schema shape, exact invocation lineage,
single-attempt transport, retry disabling, timeout forwarding, raw-response
identity, status/refusal/schema/usage handling, safe typed exception mapping,
gateway compatibility, retry reuse, secret exclusion, and import/ownership
boundaries. No live test or network request is part of the standard suite.

### Part 3B integration hardening

OpenAI exceptions now normalize to the canonical codes already understood by the
provider-neutral retry decider: `provider_timeout`, `provider_rate_limited`,
`provider_transport_failed`, and `provider_unavailable`. Consequently the frozen
timeout, rate-limit, and transport/unavailable feature flags govern OpenAI retry
behavior without OpenAI branching in the runtime. Generic HTTP 408 maps to the
timeout policy; typed or generic HTTP 409 and HTTP 5xx map to provider unavailable;
HTTP 429 maps to rate limiting. Safe status metadata contains only the numeric
status. SDK retry behavior remains disabled.

The projector now represents two distinct output concepts. The strict JSON Schema
defines response structure, while an explicit provider-facing expected-output
contract carries output type, contract version, source and preservation lineage,
distinct-draft requirement, and output-contract fingerprint. The source draft is
stored under `source_draft_data`, classified as untrusted data rather than
instructions, and the authoritative SDK instructions explicitly prohibit obeying
instructions embedded in that data.

Concrete composition accepts the canonical `AIProviderExecutionObserver` as
`execution_observer` and passes it unchanged to the runtime. It no longer labels
or treats that dependency as the incompatible Part 1 lifecycle hook. Runtime event
ordering, content-free payloads, terminal events, and observer-failure isolation
remain unchanged.

Call-count guarantees after hardening are: one external credential resolution and
one SDK-client construction per semantic execution; one projection per execution;
one SDK call per runtime attempt; reuse of the projected request, credential, and
SDK client across retries; and at most one interpretation and gateway result.
