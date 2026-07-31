# Module 2.9 Phase 7.2 Revision 10 — Concrete OpenAI Executor

Status: Implemented — awaiting independent verification

## Purpose and orchestration

`OpenAIProviderExecutorV2` is the first concrete implementation of the
provider-neutral `ProviderExecutorV2` protocol. It is an orchestration boundary,
not an SDK adapter or transport implementation:

```text
ProviderExecutionRequestV2
        ↓ strict reconstruction
pre-dispatch cancellation check
        ↓
build_openai_execution_request
        ↓
injected_client.complete(request)
        ↓ strict response reconstruction
project_openai_execution_response
        ↓ strict result reconstruction
ProviderExecutionResultV2
```

Provider semantics remain owned by the verified DTOs and pure request/response
mappings. The executor does not duplicate them.

## Constructor injection and ownership

The constructor requires an explicit object satisfying `OpenAIExecutionClientV2`
and a valid `OpenAIExecutionConfigV2`. Client validation accepts only ordinary
classes whose metaclass is exactly `type`. It bypasses normal metaclass dispatch
with builtin `type.__getattribute__`, obtains the ordinary class hierarchy and
exact class namespaces, and scans those static mapping proxies directly. Only
ordinary functions, exact `staticmethod`, and exact `classmethod` lifecycle
shapes with compatible signatures are accepted.

Callable shape is derived from a metadata-free clone of the exact Python function
and inspected with wrapped-function following disabled. Function `__signature__`,
`__wrapped__`, and function-dictionary metadata provide no validation authority.
The real code object, defaults, keyword defaults, and closure determine the
accepted caller-visible shape; annotations remain non-authoritative as in the
preceding executor revision.

Custom metaclasses are rejected before any class metadata lookup. This conservative
restriction prevents a client metaclass from executing user-controlled
`__getattribute__` or `__getattr__` code during construction. Validation never
resolves a bound method or executes client-owned instance lookup, class lookup,
metaclass lookup, properties, cached properties, or custom descriptors. Dynamic
lifecycle methods and custom instance attribute-lookup hooks are rejected
deterministically. Configuration is defensively reconstructed. There is no optional client,
service locator, singleton, global state, environment lookup, runtime discovery, or
automatic registration.

The executor does not create, connect, authenticate, close, or dispose the client.
The future composition layer owns the already-authorized client capability.

Construction also pins the exact raw function, invocation kind, and required
receiver in private frozen executor state. Execution invokes that retained function
directly: instance methods receive the retained client, class methods receive the
retained ordinary client class, and static methods receive no implicit receiver.
There is no later `client.complete` lookup. Post-construction class replacement,
deletion, descriptor replacement, or instance shadowing therefore cannot replace
the constructor-authorized callable.

## Call and cancellation guarantees

Invalid requests and requests already cancelled before dispatch cause zero client
calls. Every other valid request invokes only the pinned constructor-authorized
function, exactly once, after request reconstruction, cancellation checking, and
request mapping. There is no retry, recursion, cache, or memoization.

Cancellation is an immutable pre-dispatch snapshot. A cancelled request is strictly
reconstructed, is not mapped or dispatched, and returns a deterministic cancelled
result. Mid-flight cancellation is not supported.

## Timeout

The verified declarative timeout value is copied unchanged into the OpenAI request
DTO. The executor starts no timer, reads no clock, computes no deadline, and sleeps
nowhere.

## Failure translation

- Invalid authority or configuration raises `ExecutionConfigurationError` before
  client invocation.
- A client exception becomes a deterministic internal-execution failure.
- A malformed client response becomes a deterministic internal-execution failure.
- A response projection failure becomes a deterministic internal-execution failure.
- Valid client categories continue through the verified response mapper.

Failure messages never include client exception text, response representations,
request representations, stack traces, credentials, or transport data. When no
validated client response timestamp exists, the immutable request timestamp is used
for a deterministic result.

## Explicit exclusions

Revision 7 includes no OpenAI SDK, real client, HTTP, networking, credentials,
environment access, retry, backoff, streaming, persistence, logging, telemetry,
metrics, tracing, timers, threads, asyncio, provider discovery, registration, or
composition changes.

A future separately reviewed SDK revision may implement
`OpenAIExecutionClientV2`. It must remain injected into this executor and preserve
all verified DTO and mapping boundaries.
