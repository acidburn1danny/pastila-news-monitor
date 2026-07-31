# Module 2.9 Phase 7.2 Revision 4 — Deterministic Execution Test Harness

**Status: IMPLEMENTED — AWAITING INDEPENDENT VERIFICATION**

## Purpose

Revision 4 supplies a deterministic harness for exercising the verified Phase
7.2 execution contracts. It is not a provider, runtime adapter, SDK wrapper, or
production executor. It performs no external work and exists solely to validate
the execution boundary predictably.

The dependency direction is:

```text
provider_v2 (FROZEN)
        ↑
provider_execution_v2
        ↑
provider_execution_testing_v2
```

Neither the frozen provider core nor the verified execution-contract package
imports the testing package.

## Public API

The testing package exports only:

- `FakeProviderExecutorV2`;
- `ExecutionScenarioV2`.

`FakeProviderExecutorV2` structurally satisfies `ProviderExecutorV2` but has no
provider-specific behavior.

## Deterministic scenarios

The scenario is fixed when the harness is constructed:

- `completed` returns a completed execution result containing the validated
  projection supplied at construction;
- `provider_failure` returns a neutral deterministic provider failure;
- `timeout` returns a neutral deterministic timeout;
- `cancelled` returns a neutral deterministic cancellation;
- `internal_failure` returns a neutral deterministic internal execution failure.

Every result uses the request's validated identifiers and the fixed aware
timestamp `2000-01-01T00:00:00+00:00`. The harness never reads a clock, generates
an identifier, retries, sleeps, or randomizes behavior.

## Validation and immutability

Each request is intrinsically revalidated through `ProviderExecutionRequestV2`
before a result is created. Completed projections are strictly reconstructed at
construction and again by the execution-result boundary. Caller-owned requests
and projections are never mutated.

Each call appends a frozen private record containing the validated request,
selected scenario, and returned result. `history` returns an immutable tuple
snapshot, `last_execution` returns the latest frozen record, and
`execution_count` reports the current count. `reset()` clears only the private
history list and leaves scenario, projection, requests, and results unchanged.

## Explicit exclusions

This revision contains no:

- OpenAI, Claude, Gemini, Ollama, or other provider execution;
- SDK or HTTP integration;
- networking or authentication;
- credentials or environment access;
- retries, backoff, rate limiting, fallback, or streaming;
- filesystem, database, cache, or persistence behavior;
- logging, tracing, metrics, or telemetry;
- timers, sleeping, threads, subprocesses, or asyncio;
- provider selection, registration, or runtime discovery.

Future SDK adapters remain separate, later revisions above this test-harness
layer. This harness does not authorize or implement them.
