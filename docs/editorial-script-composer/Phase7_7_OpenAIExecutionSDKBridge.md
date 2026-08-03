# Module 2.9 Phase 7.7 Revision 6 — OpenAI Execution–SDK Bridge

Status: Revision 6 implemented, awaiting independent verification.

## Purpose

The verified execution client sends `OpenAIExecutionRequestV2`, while the frozen
SDK client accepts `OpenAISDKRequestV2`. The bridge is an offline-only
compatibility client between those contracts. It does not alter either lower
layer.

The bridge depends on the execution and SDK packages; neither lower package
depends on the bridge. It owns no credential, SDK construction, runtime
composition, transport, networking, retry, fallback, or lifecycle behavior.

## Request boundary

The bridge accepts only the exact `OpenAIExecutionRequestV2` type. It checks
exact nested message types, performs a strict dump and reconstruction, and
rejects copied-invalid state. Cancellation and nonempty stop sequences are
unsupported and are rejected before SDK invocation.

The frozen `build_openai_sdk_request()` mapper is the sole request projection.
The bridge reconstructs its exact `OpenAISDKRequestV2` result and verifies exact
preservation of model, ordered roles and content, timeout, temperature, maximum
output tokens, and the empty stop tuple. It adds no prompt content or metadata.

## SDK and response boundary

Revision 4 exposed an import-time blocker: capturing frozen SDK authority from
the passive client module transitively loaded `openai`, whose import inspected
credential-bearing SDK configuration. Revision 5 separates the passive bridge
contract from an explicit trusted bootstrap. Importing the package root,
`client`, or `errors` loads neither the SDK package nor `openai` and performs no
OpenAI-related environment reads. The private `bootstrap` module is not imported
or exported by the package root.

Explicitly importing that private bootstrap is an operational dependency-loading
decision by a future trusted composition root. It may transitively load the
official Python package. In the installed dependency environment, that import
has inspected `OPENAI_LOG`, `OPENAI_API_TYPE`, `OPENAI_API_VERSION`,
`AZURE_OPENAI_ENDPOINT`, and the credential-bearing `AZURE_OPENAI_AD_TOKEN`.
`OPENAI_API_KEY` was not observed during the repeated bootstrap audits. The
bridge supplies, stores, logs, or deliberately retrieves no credential value.
It does not construct an official client, compose runtime, or perform a
provider/network operation. Passive bridge imports perform zero OpenAI/Azure
environment inspection.

Bootstrap requires one exact `OpenAISDKClientV2`. The bridge statically
validates the class namespace without descriptor execution. Revision 3 accepted
any signature-compatible plain function installed before construction; its
independent verification identified that behavior as an authority-redirection
blocker. Revision 4 captures the exact frozen `OpenAISDKClientV2.complete`
function during explicit trusted bootstrap initialization. Minting succeeds
only when the statically inspected class attribute is that identical object.
Wrappers, clones, copied metadata, static/class methods, properties, and custom
descriptors are rejected. The exact trusted function and supplied exact receiver
are then pinned. Ordinary replacements both before and after construction cannot
redirect bridge execution.

The frozen `build_openai_sdk_request` function is captured at the same explicit
bootstrap boundary. Later replacement of its public module attribute does
not redirect mapping, and no competing projection is introduced. Caller input
is fully reconstructed and compatibility-checked before mapping. An unexpected
mapper exception, wrong return type, copied-invalid return, or incoherent mapped
DTO is therefore a dependency failure; caller request and compatibility
failures remain configuration errors.

This is a same-process identity guarantee with a specific trust boundary:
project-owned verified modules must initialize cleanly at explicit bootstrap.
Hostile mutation before bootstrap initialization,
private anchor mutation, `sys.modules` replacement, compromised import hooks,
code-object mutation, debugger access, and memory instrumentation are out of
scope. Private globals provide identity authority, not secrecy or a general
Python security boundary.

Direct construction is permanently rejecting; only the atomic private bootstrap can
create a bridge after bootstrap has validated and pinned the exact receiver,
`complete` function, mapper, and SDK request type. Revision 5 used an extractable
module-level token and raw mint helper; independent verification demonstrated
that private naming was not authorization. Revision 6 removes both primitives.
The atomic bootstrap accepts only `sdk_client`, resolves all other authority
internally, and initializes the bridge inline. No module-level function accepts
caller-supplied receiver, callable, mapper, request type, or authority token.

The first successful bootstrap establishes one immutable authority generation
containing only the exact SDK client class, `complete` function, mapper, and SDK
request type. It retains no client, bridge, request, response, credential,
transport, result, or failure history. Every later bootstrap resolves current
SDK authority again and requires identity with that generation. Callable or
mapper mutation causes rejection; restoring the authentic objects permits a
later bootstrap without replacing the original generation. Each accepted SDK
client produces an independent bridge and is never cached globally.

The bootstrap is intentionally importable through its private module path by a
future trusted composition root. Private naming is not a security boundary.
Direct hostile construction with `object.__new__`, private slot mutation,
compromised imports, debugger/memory instrumentation, and mutation before the
first trusted bootstrap event remain outside this same-interpreter contract.
No public authority token, bootstrap function, mapper, or SDK type is exported.

Every valid bridge call invokes the pinned SDK function exactly once. There is
no retry, fallback, polling, or recursion introduced by the bridge.

The frozen SDK client already converts its private SDK response into
`OpenAIExecutionResponseV2`; consequently this package adds no competing
response mapper. It requires the exact returned type and strictly reconstructs
it, preserving response identity, model, timestamp, ordered output fragments,
text, finish reasons, status, failure category, and failure code. It never joins
or trims output, invents timestamps, or rewrites partial results.

## Errors and object behavior

Caller incompatibility produces a fixed configuration error. SDK-client
failure, trusted mapper failure or incompatibility, and malformed returned state
produce a fixed dependency error. Ordinary exception text and request, response, client, model,
prompt, timeout, and identity data are not exposed. Public errors suppress
ordinary exception context and cause. `KeyboardInterrupt`, `SystemExit`, and
`GeneratorExit` propagate unchanged; their interpreter-owned traceback cannot
be made secret against hostile same-process inspection, although bridge frames
delete sensitive locals where practical.

The bridge is immutable, copy-stable, non-serializable, stateless between calls,
and safe for reentrant use under the responsibility of the injected synchronous
SDK capability. Its representation is always
`OpenAIExecutionSDKBridgeClientV2()`.

## Milestone boundaries

Revision 6 remains entirely offline and must pass independent verification
before higher bridged runtime composition begins. The next separately authorized
revision is reserved for that composition and its single lifecycle authority.
Phase 7.8 remains reserved for separately authorized live execution.
