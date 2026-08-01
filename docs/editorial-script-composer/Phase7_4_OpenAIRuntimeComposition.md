# Module 2.9 Phase 7.4 Revision 5 — Active-Exception Context Isolation

Status: Implemented — awaiting independent verification

## Purpose and dependency direction

This specification-only package defines trusted runtime composition above the
frozen Phase 7.3 SDK adapter:

```text
provider_v2
    ↑
provider_execution_v2
    ↑
provider_execution_openai_v2
    ↑
provider_execution_openai_sdk_v2  [FROZEN]
    ↑
provider_runtime_openai_v2
    ↑
future application composition root
```

Lower layers do not import this package. It performs no automatic registration and
has no composition-root or peer-provider dependency.

## Trust model

Application startup, runtime composition, injected credential sources, injected
SDK factories, and project-owned production modules are trusted. Credential values
before validation, provider requests and responses, SDK exception payloads, and
external provider behavior are untrusted.

Malicious Python already executing in-process, project-internal monkeypatching,
debugger or memory instrumentation, and deliberate mutation of private state are
out of scope. Python privacy, frozen models, slots, closures, sentinels, and module
globals are not anti-tamper security boundaries.

## Runtime configuration

`OpenAIRuntimeConfigV2` is strict, immutable, extra-forbidding, and defensively
revalidated. It contains only `enabled`, exact built-in integer `max_retries=0`,
and a positive finite request timeout. It contains no API key, header, bearer token,
HTTP client, transport, organization, or project data.

## Credential-source boundary

`OpenAICredentialSourceV2` is explicitly injected and exposes only
`get_api_key()`. Construction validates its static method shape without binding or
executing descriptors, lookup hooks, or the method body. Revision 2 never calls it.

A future retrieved key must be an exact built-in string, nonempty,
non-whitespace-only, and unpadded. Keys never enter errors, public DTOs, results,
logs, or representations. No environment-backed source, `.env` parsing, prefix
assumption, or `OPENAI_API_KEY` access exists in this revision.

## SDK-factory boundary

`OpenAISDKFactoryV2` is explicitly injected. Its synchronous `create_client` shape
accepts only the future `api_key` and exact `max_retries=0` policy; `close_client`
represents lifecycle cleanup. Static validation ignores forged `__signature__` and
`__wrapped__` metadata and rejects descriptors, custom lookup, incompatible shapes,
and async factories without executing controlled code.

Normal package import loads no official SDK type, constructs no `OpenAI(...)` client,
and calls neither factory operation. A missing SDK will become a fixed, localized
`OpenAIRuntimeDependencyError` in the operational revision.

## Lifecycle ownership and composition result

Future successful composition owns exactly the SDK client it constructs. The
immutable `OpenAIRuntimeCompositionV2` accepts only exact `OpenAISDKClientV2` and
`OpenAIProviderExecutorV2` objects, requires the executor to reference that same SDK
client, and accepts only the private project-owned lifecycle owner. Direct malformed,
lookalike, subclass, incomplete, or contradictory combinations are rejected with
fixed safe errors. The lifecycle owner is private and excluded from representations.
The result exposes no raw SDK client, credential, source, factory, headers,
transport, callback, or exception.

The public representation is fixed symbolic text. It invokes no nested
representation and reveals no object address. The only mutable detail is private
close-once state owned by the lifecycle object. Cleanup is synchronous, idempotent,
and at most once: the owner marks itself closed before invoking its pinned close
operation. A cleanup failure maps to fixed `OpenAIRuntimeLifecycleError` without
context or cause, remains permanently closed, and is never retried. This mechanism
assumes single-threaded lifecycle use and does not claim thread safety.

The composition and its private owner are immutable ownership handles. Both
`copy.copy()` and `copy.deepcopy()` return the same object, before or after cleanup,
so copying cannot duplicate ownership or invoke nested copy hooks. Dataclass
replacement is unsupported because ownership handles are not dataclasses. Pickling
and other reduction-based serialization reject deterministically rather than create
a second owner.

Cleanup execution produces only an immutable safe outcome. All frames holding the
composition, lifecycle owner, callback, receiver, SDK client, executor, or raw
failure exit before a separate clean helper raises the fixed public lifecycle error.
Adapter-owned traceback locals therefore retain only the safe outcome and no runtime
ownership state. Context, cause, and module globals retain no cleanup failure or
history.

Ownership transfers only after complete successful construction. Credential failure
creates no client; factory failure returns no composition; capability, adapter, or
executor assembly failure must close an owned client exactly once; successful
composition transfers the client to the lifecycle owner; composition close performs
cleanup exactly once. No partial composition result is returned. Revision 2 remains
specification-only and performs no client construction or close operation in the
production composer.

## Startup validation and non-operational behavior

`OpenAIRuntimeComposerV2` reconstructs runtime policy and statically validates the
required credential source, synchronous factory, and close lifecycle shapes. It
rejects invalid retry policy, copied-invalid config, missing dependencies,
descriptors, lookup hooks, forged callable metadata, incompatible callables, and
async factories without retrieving credentials or calling a factory.

`compose()` remains deliberately non-operational and produces an immutable,
nonsensitive dependency-failure outcome containing only a fixed category and fixed
message. The frame that held the composer and its injected dependencies removes that
reference before a separate clean helper raises the fixed
`OpenAIRuntimeDependencyError`: `OpenAI runtime composition is not implemented`.
Runtime-package traceback frames retain only that safe outcome. The public error
retains no composer, config, credential source, SDK factory, dependency state, raw
exception, representation, credential, or transport. Repeated failures retain no
module-global history. Credential-source and factory invocation counts remain zero.
The Revision 3 lifecycle behavior is unchanged, and no usable runtime result is
fabricated.

Revision 5 additionally isolates both dependency and lifecycle errors from an
unrelated exception already active in the caller. `raise ... from None` alone only
suppresses displayed chaining and does not clear stored implicit context. Each fresh
public error is therefore raised once and has its context, cause, and suppression
state explicitly sanitized in the raising frame's `finally` path before propagation
completes. This mechanism never reads, represents, or classifies the active caller
exception. Normal, active-handler, and nested-handler failures retain no caller
exception state and keep their fixed safe messages. Runtime traceback locals contain
only the safe outcome and fresh public error. Composer behavior remains
non-operational, and lifecycle ownership and close-once behavior are unchanged.

## Retry responsibility

The runtime policy requires exact built-in integer zero. In the operational revision, trusted
composition must pass `max_retries=0` to official `OpenAI(...)` construction and
then build `OpenAISDKCapabilityV2`. Phase 7.3 guarantees exactly one adapter-level
capability invocation; neither layer claims proof of one SDK-internal or HTTP
transport attempt.

## Errors and import isolation

The public taxonomy separates composition, configuration, credential, dependency,
and lifecycle failures. Messages are fixed and contain no credential value, raw
exception text, object representation, memory address, header, body, or transport.

Clean import performs no credential/environment read, SDK construction, network,
registration, or observable output. Frozen lower layers do not load this package.

## Operational exclusions

Revision 2 has no credential acquisition, `.env` access, environment access,
official SDK construction, live request, network, streaming, async execution,
application retry, persistence, logging, telemetry, metrics, tracing, provider
discovery, automatic registration, or application composition-root integration.

## Operational revision responsibilities

A separately scoped and independently verified future revision may add the official SDK
factory, an injected credential implementation, `max_retries=0` client construction,
client lifecycle and failure atomicity, capability assembly, startup validation,
and an explicitly opt-in live smoke-test specification. It must remain above and
must not modify the frozen Phase 7.3 package.
