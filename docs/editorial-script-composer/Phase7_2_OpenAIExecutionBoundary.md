# Module 2.9 Phase 7.2 Revision 5 — OpenAI Execution Boundary

Status: Implemented — awaiting independent verification

## Purpose and dependency direction

Revision 5 specifies a provider-specific but transport-neutral OpenAI boundary. It
does not execute requests. The dependency direction is strictly:

```text
provider_v2 (frozen)
        ↑
provider_execution_v2 (verified)
        ↑
provider_execution_openai_v2
        ↑
future injected OpenAI client implementation
```

The frozen registry remains responsible only for discovery, validation, authority,
and composition. It does not know about this execution boundary and gains no
execution method.

## Contracts

`OpenAIExecutionConfigV2` contains only model-generation controls: model,
temperature, maximum output tokens, and stop sequences. Credentials, endpoints,
headers, organization identifiers, SDK options, and transport settings are absent.

`OpenAIExecutionRequestV2` is an immutable DTO containing the authoritative
execution request identifier, frozen request-envelope identity, ordered messages,
timeout budget, cancellation snapshot, and generation controls. The pure request
mapper accepts only the exact frozen OpenAI descriptor authority. Message traversal
and role mapping are deterministic:

| Provider-neutral role | OpenAI boundary role |
| --- | --- |
| `instruction` | `system` |
| `context` | `user` |
| `generation` | `user` |

`OpenAIExecutionResponseV2` is an immutable future-client response DTO. The pure
response mapper projects it into the verified provider-neutral execution result and
reuses frozen result-envelope construction to validate output coverage and lineage.

`OpenAIExecutionClientV2` is a protocol only. Revision 5 supplies no conforming
implementation, SDK wrapper, executor, transport, fake client, or runtime factory.

## Result and failure mapping

Provider-result status remains distinct from execution outcome:

| OpenAI boundary category | Execution outcome |
| --- | --- |
| no client category | `completed` with frozen provider-result semantics |
| `content_filtered` | `completed` with partial provider-result semantics |
| `authentication` | `provider_failure` |
| `rate_limited` | `provider_failure` |
| `invalid_request` | `provider_failure` |
| `provider_unavailable` | `provider_failure` |
| `timeout` | `timeout` |
| `cancelled` | `cancelled` |
| `malformed_response` | `internal_execution_failure` |
| `internal_client_error` | `internal_execution_failure` |

A provider-declared failed result without a client failure category is still a
completed execution attempt carrying failed provider-result semantics. Content
filtering likewise remains a provider semantic rather than a transport failure.

## Timeout, cancellation, and credentials

The timeout is a declarative budget copied from `TimeoutPolicyV2`; this revision
creates no timer. Cancellation is a snapshot copied from the provider-neutral
cancellation token; a future executor is responsible for checking it before
dispatch. No threading or asynchronous cancellation mechanism is introduced.

Credential resolution and secret handling are responsibilities of a future
dependency-injected client implementation. Credentials never enter these DTOs,
pure mappings, errors, or package imports.

The future real executor must receive an already-authorized object satisfying
`OpenAIExecutionClientV2` through explicit constructor injection. Service locators,
global client singletons, environment-driven executor construction, runtime
discovery, and automatic registration are excluded.

## Retry and streaming policy

Automatic retries are unsupported and the default is no retry. Retry counts and
backoff do not belong to Revision 5 configuration; any future retry policy requires
a separate verified revision. Streaming is also unsupported: there are no chunk
DTOs, generators, callbacks, or synchronous/asynchronous streaming protocols.

## Explicit non-goals

Revision 5 contains no SDK imports, HTTP, networking, authentication, environment
access, API keys, retries, backoff, rate limiting, streaming, persistence,
telemetry, metrics, logging, tracing, runtime provider discovery, timers, threads,
or asynchronous execution. It does not modify provider registration, Phase 7.1,
the verified execution contracts, or the deterministic test harness.

## Future Revision 6 responsibilities

A later revision may provide a concrete dependency-injected client and executor.
That work must translate SDK-specific exceptions into the frozen client categories,
honor the timeout and cancellation contracts, preserve response DTO validation,
and keep credentials outside all artifacts. It must not move transport concerns
into the registry or provider-neutral contracts.

## Public API

The package exports exactly 14 symbols: five boundary error types, one client error
category, five immutable DTOs, one client protocol, and two pure mapping functions.
Internal helpers are not public.

## Revision 6 semantic reconciliation

Revision 6 makes content-filter classification bidirectional and exact. A response
classified as `content_filtered` must use partial provider semantics, contain at
least one output, carry a failure code, and give every output the frozen
`content_filtered` finish reason. Conversely, any content-filtered output requires
that category, partial status, and failure code. Mixed or contradictory finish
reasons are rejected; the boundary never rewrites, drops, or repairs them.

Content-filtered outputs may preserve nonempty partial generated text. Empty text
remains forbidden by the existing frozen output contract, and no text is changed by
projection.

The request DTO now validates stop sequences autonomously using the same private
policy as configuration: strict built-in strings, no empty, whitespace-only,
padded, or duplicate entries, and preserved caller order. List inputs are copied
into immutable tuple storage. Public reconstruction rejects invalid instances made
with `model_copy()` for both corrected areas.

This correction adds no executor, SDK, networking, credentials, retry, streaming,
registration, or runtime behavior. The 14-symbol public API is unchanged.
