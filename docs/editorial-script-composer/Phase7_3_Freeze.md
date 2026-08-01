# Module 2.9 Phase 7.3 Freeze

## Identification

- Module: 2.9
- Phase: 7.3
- Verified revision: Revision 6
- Verified status: `PHASE_7_3_REVISION_6_VERIFIED`
- Git commit: `d47d69b0fb9ce6f4c6a7539808ccd4debfc819cd`
- Git tag: `module-2.9-phase-7.3-r6-verified`
- Branch at freeze creation: `feature/openai-sdk`

## Purpose

Phase 7.3 is a provider-specific OpenAI SDK execution boundary and synchronous
operational adapter layer built above the verified provider-neutral execution
contracts. It does not include runtime credential composition or automatic SDK
client construction.

## Dependency direction

```text
provider_v2
    ↑
provider_execution_v2
    ↑
provider_execution_openai_v2
    ↑
provider_execution_openai_sdk_v2
    ↑
future trusted runtime composition
```

There is no reverse dependency, generic-core SDK dependency, composition-root
dependency, peer-provider dependency, or automatic registration.

## Public API snapshot

`provider_execution_openai_sdk_v2` exports exactly 10 symbols:

1. `OpenAISDKBoundaryError`
2. `OpenAISDKCapabilityV2`
3. `OpenAISDKClientV2`
4. `OpenAISDKConfigurationError`
5. `OpenAISDKDependencyError`
6. `OpenAISDKRequestV2`
7. `OpenAISDKResponseError`
8. `build_openai_sdk_request`
9. `classify_openai_sdk_exception`
10. `reconstruct_openai_sdk_response`

Baseline export counts are:

- `provider_v2`: 42
- `provider_execution_v2`: 13
- `provider_execution_testing_v2`: 2
- `provider_execution_openai_v2`: 15
- `provider_execution_openai_sdk_v2`: 10

## Trust model

Trusted components are application composition, project-owned production modules,
the composition-created official SDK capability, and ordinary Python execution
without hostile mutation of internal project state.

Untrusted inputs are provider requests, copied-invalid DTOs, SDK/provider responses,
provider exception payloads, and external provider behavior.

Arbitrary malicious Python already running in the same interpreter, private-module
mutation, deliberate `object.__new__` or `object.__setattr__` compromise,
monkeypatching project-owned internals, and debugger or memory-instrumentation
attacks are explicitly out of scope. Python private names, frozen dataclasses,
slots, closures, sentinels, and module globals are not security boundaries against
arbitrary same-process code execution.

## Capability and dispatch guarantees

The verified boundary provides explicit capability injection with no automatic SDK
client construction or credential lookup. It statically validates callable shape
without executing descriptors or lookup hooks, pins the exact adapter-level
callable and receiver, and performs no fresh adapter-level callable lookup during
`complete()`.

Each valid dispatch performs exactly one adapter-level capability invocation. The
adapter implements no application retry, fallback, polling, recursion, or secondary
API. This is not a claim of exactly one network request or SDK transport attempt,
tamper-proof same-process authority, or cryptographic capability sealing.

## Retry policy

The adapter validates a trusted-composition-supplied `max_retries` policy requiring
exact built-in integer zero. The runtime composition layer remains responsible for
constructing the official OpenAI client with `max_retries=0`.

The adapter guarantees one capability invocation. It does not independently prove
the number of internal SDK or HTTP attempts.

## Request guarantees

The boundary provides strict SDK request reconstruction; exact model, role,
content, temperature, and maximum-output-token preservation; ordered message
preservation; fractional timeout preservation; and explicit `store=False`,
`stream=False`, and `background=False`. Nonempty stop sequences are rejected.
It adds no hidden instructions, tools, metadata, runtime headers, or credential
fields.

## Response guarantees

The boundary provides strict external response reconstruction, closed terminal-state
mapping, cross-field terminal-state reconciliation, output-item status validation,
contradiction and unsupported-state rejection, deterministic output ordering,
whitespace-only output rejection, and exact meaningful-text preservation. It
retains no raw SDK object, header, or transport. Timestamps are validated
deterministically without inventing current time.

Supported terminal mappings are:

| Provider state | Finish reason |
|---|---|
| `completed` | `stop` |
| `incomplete/max_output_tokens` | `length` |
| `incomplete/content_filter` | `content_filter` |

## Exception guarantees

Exception classification uses trusted structured authority rather than free-form
message text. The adapter does not catch `BaseException`. Public error text is
fixed, with `__context__` and `__cause__` absent. Production has no global request
or failure cache, and adapter module globals retain no request-specific or raw
exception state. Request-bearing execution exits before safe public error raising.
These guarantees do not claim protection against a debugger or arbitrary frame
introspection outside the documented trust model.

## Operational exclusions

Phase 7.3 excludes credential acquisition, `.env` and `OPENAI_API_KEY` access,
`OpenAI(...)` construction, official-client lifecycle management, a runtime
composition root, live API smoke testing, streaming, async execution, automatic
retry, persistence, logging, telemetry, metrics, tracing, provider discovery, and
automatic registration.

## Frozen compatibility guarantees

- Phase 7.1 hashes: 15/15 match
- OpenAI delegated callable identities: 8/8 unchanged
- `provider_v2` exports: 42
- `provider_execution_v2` exports: 13
- `provider_execution_testing_v2` exports: 2
- `provider_execution_openai_v2` exports: 15
- `provider_execution_openai_sdk_v2` exports: 10

## Freeze policy

After formal freeze, no frozen production file may be modified casually. Any change
requires a new explicit corrective revision. New runtime composition must live
above the frozen package. Future Ollama, Claude, or Gemini implementations must not
modify the frozen OpenAI boundary.

Any unavoidable modification requires explicit scope, independent verification,
an updated integrity manifest, a new Git commit and tag, and documented
compatibility impact.

## Future authorized work

The next allowed phase is **Phase 7.4 — Trusted OpenAI Runtime Composition**. Its
responsibilities are official SDK client construction, credential injection,
`max_retries=0`, client lifecycle, capability assembly, startup validation, and an
opt-in live smoke-test specification.

Phase 7.4 must depend on Phase 7.3 and must not modify frozen Phase 7.3 files unless
a separately verified corrective revision is approved.
