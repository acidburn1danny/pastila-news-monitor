# Module 2.9 Phase 7.6 Revision 1 — Canonical Smoke Request Authority

Status: Implemented — awaiting independent verification

## Purpose

Phase 7.5 proved that the verified offline smoke runner and verified production
runtime cannot honestly create a live request by themselves. Neither layer owns
the execution-plan, draft, source-request, request-identity, timestamp, and timeout
authority required by `ProviderExecutionRequestV2`.

Phase 7.6 introduces the higher-layer smoke-domain authority that will eventually
own that projection. Revision 1 defines and validates the canonical smoke plan but
deliberately does not construct a provider execution request.

The dependency direction is:

```text
provider_v2
    ↑
provider_execution_v2
    ↑
provider_execution_openai_v2
    ↑
provider_runtime_openai_v2
    ↑
provider_runtime_openai_smoke_v2
    ↑
provider_smoke_request_authority_v2
    ↑
future trusted application composition root
```

No lower layer imports this package.

## Canonical smoke semantics

`SmokeExecutionPlanV2` represents one real, stable smoke-domain operation. It has:

- plan reference `canonical-smoke-plan-v2`;
- draft reference `canonical-smoke-draft-v2`;
- source-request reference `canonical-smoke-source-request-v2`;
- exactly one request unit at ordinal `0`;
- exactly one generation message at ordinal `0`;
- exactly this UTF-8 content:

```text
Reply with exactly:

SMOKE_OK
```

The plan permits no context or system messages, metadata, tools, images, caller
prompt, extra unit, or additional instruction. The prompt is defined once inside
the plan authority and is not accepted from callers.

## References, identities, and fingerprints

References are derived canonical domain references rather than random identifiers.
They describe the stable operation, draft, and source request, not a particular
runtime attempt.

`build_canonical_smoke_execution_plan()` is the sole public minting function. It
uses the frozen `provider_v2` canonical UTF-8 JSON and SHA-256 implementation.
Canonical mappings are key-sorted, strings are NFC-normalized, JSON is compact,
and domain labels separate the draft, plan identity, and plan fingerprint.

The draft fingerprint covers the fixed draft reference and exact ordered message.
The plan identity covers the canonical plan semantics without self-seals. The plan
fingerprint covers the canonical plan identity and semantics under a distinct seal
domain. Python `hash()`, object identity, memory addresses, arbitrary `repr()`,
randomness, clocks, and nondeterministic JSON ordering are not used.

Every `SmokeExecutionPlanV2` reconstructs and verifies all three seals. Copied or
manually changed identities, fingerprints, references, units, roles, ordinals, or
content are invalid.

## Request identity and timestamp ownership

The stable plan does not own a runtime attempt identifier or timestamp. A future
trusted application composition root will supply them explicitly. Private
specification protocols describe synchronous request-ID and timestamp sources;
they are not invoked or exported in Revision 1.

The future construction boundary accepts an exact built-in, nonblank, unpadded
request ID of at most 200 characters. It accepts only an exact `datetime` whose
timezone is the canonical `datetime.UTC` singleton. Naive, implicit-local, custom
timezone, and non-datetime values are rejected. No clock or randomness is accessed
during import or validation.

## Timeout ownership

The trusted application root supplies the timeout for a particular attempt. The
boundary accepts an exact positive built-in integer or a finite positive built-in
float. Booleans, coercible objects, strings, zero, negative, infinity, and NaN are
invalid. Integers are not converted to floats and no default override exists.

A future revision will project the exact value into `TimeoutPolicyV2` and require
coherence with the production runtime configuration.

## Provider authority and future projections

The future root targets only the canonical `OpenAIProviderAdapter.descriptor`. It
will not mint or modify a provider descriptor.

The intended pure projection is:

| Smoke authority | `ProviderRequestIntentV2` |
|---|---|
| plan reference | execution-plan reference |
| plan identity | execution-plan identity |
| plan fingerprint | execution-plan fingerprint |
| draft reference | draft reference |
| draft fingerprint | draft fingerprint |
| source-request reference | sole request-unit source reference |
| unit ordinal `0` | request-unit ordinal `0` |
| role `generation` | message role `generation` |
| exact fixed content | message content |
| message ordinal `0` | message ordinal `0` |

The future sequence is:

```text
SmokeExecutionPlanV2
    ↓
ProviderRequestIntentV2
    ↓
build_provider_request_envelope(intent, OpenAIProviderAdapter.descriptor)
    ↓
ProviderRequestEnvelopeV2
    ↓
ExecutionContextV2(explicit request ID, explicit UTC timestamp)
    ↓
TimeoutPolicyV2(explicit timeout)
    ↓
ProviderExecutionRequestV2
```

Revision 1 stops before the first provider DTO. It neither duplicates the frozen
envelope seals nor fabricates a downstream request.

## Non-operational construction shell

`SmokeProviderExecutionRequestAuthorityV2.construct()` accepts only:

- a canonical `SmokeExecutionPlanV2`;
- an explicit request ID;
- an explicit UTC timestamp;
- an explicit timeout.

It defensively reconstructs the plan, validates every specification input, returns
an internal safe outcome, and raises the fixed
`SmokeExecutionRequestDependencyError` message `canonical smoke request
construction is not operational`. Invalid input produces the fixed
`SmokeExecutionRequestConfigurationError` message `invalid canonical smoke request
authority input`.

It never returns or constructs `ProviderExecutionRequestV2` in Revision 1.

The holder has no persistent state, copies and deep-copies by identity, has a fixed
representation, and rejects pickle. Public errors are fresh, suppress context, and
retain no plan, ID, timestamp, timeout, prompt, caller exception, or raw validation
failure.

## Trust model

Trusted:

- the future application composition root;
- project-owned canonical authority models and builders;
- the frozen canonical OpenAI provider descriptor;
- explicitly supplied request-ID and timestamp authorities after validation.

Untrusted:

- copied-invalid models;
- caller strings and timestamps;
- caller timeout values;
- future downstream provider results.

Python privacy is not a security boundary. Hostile same-interpreter mutation,
private-module monkeypatching, debugger access, and memory instrumentation remain
out of scope.

## Public API

The package exports exactly:

- `SmokeExecutionPlanV2`;
- `SmokeExecutionRequestAuthorityError`;
- `SmokeExecutionRequestConfigurationError`;
- `SmokeExecutionRequestDependencyError`;
- `SmokeProviderExecutionRequestAuthorityV2`;
- `build_canonical_smoke_execution_plan`.

Canonicalization helpers, seal internals, private source protocols, test doubles,
provider runtime types, SDK types, and CLI types are not exported.

## Non-operational scope

Revision 1 performs no credential lookup, environment access, SDK import or
construction, runtime composition, provider DTO construction, network operation,
provider call, persistence, telemetry, CLI registration, live request, or Ollama
work.

Revision 2 is reserved for canonical provider request construction after this
authority contract passes independent verification. Phase 7.7 remains reserved
for separately authorized live execution.
