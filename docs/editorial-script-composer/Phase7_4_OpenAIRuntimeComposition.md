# Module 2.9 Phase 7.4 Revision 7 — Coherent Handoff and Unique Ownership

Status: Implemented — awaiting independent verification

## Purpose and dependency direction

This package defines trusted runtime composition above the
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
revalidated. It contains an exact nonblank unpadded `model`, `enabled`, exact
built-in integer `max_retries=0`, and a positive finite request timeout. It contains
no API key, header, bearer token, HTTP client, transport, organization, or project
data.

## Credential-source boundary

`OpenAICredentialSourceV2` is explicitly injected and exposes only
`get_api_key()`. Construction validates its static method shape without binding or
executing descriptors, lookup hooks, or the method body. Each eligible `compose()`
call invokes the pinned source function exactly once.

A retrieved key must be an exact built-in string, nonempty,
non-whitespace-only, and unpadded. Keys never enter errors, public DTOs, results,
logs, or representations. No environment-backed source, `.env` parsing, prefix
assumption, or `OPENAI_API_KEY` access exists in this revision.

## SDK-factory boundary

`OpenAISDKFactoryV2` is explicitly injected. Its synchronous `create_client` shape
accepts the validated `api_key`, exact `max_retries=0`, and the positive finite
`request_timeout_seconds`; `close_client` remains part of its validated lifecycle
contract. Static validation ignores forged `__signature__` and
`__wrapped__` metadata and rejects descriptors, custom lookup, incompatible shapes,
and async factories without executing controlled code.

Normal package import constructs no `OpenAI(...)` client and calls neither factory
operation. Revision 7 adds no concrete official factory or environment-backed source.
The trusted factory must use the private one-client handoff mint. That mint statically
derives the synchronous Responses resource and pinned close authority from the same
raw client, requires weak-reference support, and returns an exact frozen handoff.
It accepts no independent Responses argument, so split execution and cleanup
provenance cannot be represented through the supported contract.

Before a valid handoff is returned, the factory owns the client and is responsible
for cleanup if minting fails. The composer never guesses cleanup for arbitrary or
malformed factory values. Ownership transfers only when the composer revalidates and
registers the exact coherent handoff.

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

One private identity tracker prevents two live owners for the same raw-client object
without invoking its equality or hash behavior. It stores only integer identities and
weak references and is not an anti-tamper security boundary. A duplicate handoff is
rejected with `OpenAI runtime client is already owned` before a second lifecycle
owner or close attempt exists. A successful close or rollback removes the live record,
so a trusted factory may begin a new ownership cycle for that same client. A failed
close or rollback instead replaces the live record with a terminal failed-cleanup
record, and every later handoff for that exact client is rejected with
`OpenAI runtime client cleanup previously failed` without another close attempt.
Trusted factories should ordinarily return a fresh client.

The private terminal record contains only the raw-client integer identity, indirectly
as its tracker key, one weak reference, and a fixed terminal state. It retains no raw
client, close authority, Responses resource, handoff, credential, factory, exception,
transport, or call history. Its weak-reference callback removes only the record that
still contains that exact weak reference. Ordinary Python object collection therefore
removes the tombstone, while a stale callback cannot affect a newer object that reuses
the integer ID. Neither acquisition nor collection invokes client equality or hashing.
This identity tracker assumes ordinary Python object lifetime and remains an internal
ownership invariant, not an anti-tamper security boundary.

Credential failure creates no client; factory failure returns no composition; every
failure after accepted registration closes the owned client exactly once and either
removes or terminally transitions its record; successful composition transfers the pinned handoff authority to the
lifecycle owner. No partial composition result is returned.

## Startup validation and operational composition

`OpenAIRuntimeComposerV2` reconstructs runtime policy and statically validates the
required credential source, synchronous factory, and close lifecycle shapes. It
rejects invalid retry policy, copied-invalid config, missing dependencies,
descriptors, lookup hooks, forged callable metadata, incompatible callables, and
async factories without retrieving credentials or calling a factory.

`compose()` defensively reconstructs configuration, retrieves and validates one
credential, invokes the injected factory once, builds the pinned Responses
capability, narrow SDK client, model-configured executor, private lifecycle owner,
and final composition. The factory receives only the unchanged key, exact integer
zero retry policy, and configured timeout. The executor receives the explicitly
configured, exact nonblank model. No request is made during assembly.

After an exact coherent handoff is revalidated and its identity registration
succeeds, the composer owns the raw client until authority is transferred to the
private lifecycle owner. The handoff's pinned cleanup function and receiver are used
without later raw-client lookup. Any later assembly failure closes and releases
through that owner exactly once. If assembly and rollback both fail, the fixed
lifecycle error `OpenAI runtime rollback failed` takes precedence; otherwise assembly
maps to the fixed dependency error `OpenAI runtime assembly failed`. Raw exceptions
and partial results never escape. Successful compositions retain only the narrow SDK
client, executor, and private owner; the composer caches no key, raw client, result,
or failure history. Each call is independent.

Revision 5 additionally isolates both dependency and lifecycle errors from an
unrelated exception already active in the caller. `raise ... from None` alone only
suppresses displayed chaining and does not clear stored implicit context. Each fresh
public error is therefore raised once and has its context, cause, and suppression
state explicitly sanitized in the raising frame's `finally` path before propagation
completes. This mechanism never reads, represents, or classifies the active caller
exception. Normal, active-handler, and nested-handler failures retain no caller
exception state and keep their fixed safe messages. Runtime traceback locals contain
only the safe outcome and fresh public error. Composer behavior remains
operational through injected offline-testable dependencies, while lifecycle ownership
and close-once behavior are unchanged.

## Retry responsibility

The runtime policy requires exact built-in integer zero. Trusted composition passes
`max_retries=0` to the injected factory and `OpenAISDKCapabilityV2`. Phase 7.3
guarantees exactly one adapter-level
capability invocation; neither layer claims proof of one SDK-internal or HTTP
transport attempt.

## Errors and import isolation

The public taxonomy separates composition, configuration, credential, dependency,
and lifecycle failures. Messages are fixed and contain no credential value, raw
exception text, object representation, memory address, header, body, or transport.

Clean import performs no credential/environment read, SDK construction, network,
registration, or observable output. Frozen lower layers do not load this package.

## Operational exclusions

Revision 6 has no `.env` access, environment access, concrete official SDK factory,
live request, network, streaming, async execution,
application retry, persistence, logging, telemetry, metrics, tracing, provider
discovery, automatic registration, or application composition-root integration.

## Operational revision responsibilities

A separately scoped and independently verified future revision may add the official
synchronous SDK factory, an injected environment credential implementation, and an
explicitly opt-in live smoke-test specification. It must remain above and must not
modify the frozen Phase 7.3 package.
