# Module 2.9 Phase 7.8 Revision 1 — Offline Live-Smoke Integration

Status: implemented, awaiting independent verification.

## Revision 6 producing-runtime configuration authority

Independent verification of Revision 5 showed that the base and bridged
executor configurations were both mutable projections. Coordinated replacement
of both models could therefore preserve their equality while losing the model
that actually produced the runtime.

Revision 6 captures the exact built-in model string from the exact base runtime
composer stored by the injected bridged composer when runner authority is
created. This runner-private value is immutable, is not exported, and is not
refreshed from later executor projections. The same exact composer is retained
to produce every composition for that runner.

Before the lower registration claim is invoked, model coherence now requires:

```text
pinned producing-runtime model
  = exact base executor model
  = exact bridged executor model
```

All three values must be exact built-in strings with identical values.
One-sided foreign models, coordinated equal foreign models, and different
foreign models fail before claim, execution, or cleanup handoff. Temperature,
maximum-output-token, and stop controls remain executor-owned; Revision 6 does
not compare them with unrelated runtime fields or impose new defaults.

This check inspects configuration only. Registration maps, ownership trackers,
leases, weak references, callbacks, and claim lineage remain exclusively owned
by the verified lower claim boundary. Claim authority, claim-result validation,
request/result lineage, exact `SMOKE_OK`, cleanup, and BaseException behavior
are unchanged from Revision 5.

## Revision 5 callable authority and configuration coherence

Independent verification of Revision 4 found two defects: the mutable local
claim alias could redirect an existing runner, and an exact but foreign executor
model could diverge from the runtime that produced the composition. Revision 5
binds the clean-import lower claim function and its exact opaque result type into
each immutable runner. Construction requires the local and lower-module aliases
to retain their original identities. Existing runners continue using their
pinned function after later alias replacement; replacement bodies and
descriptors are not invoked. Future runner construction rejects authority drift.

The trusted boundary begins at a clean import of the verified lower module.
Hostile mutation before that initialization, import-hook or `sys.modules`
replacement, debugger/memory instrumentation, and direct mutation of runner
private slots or trusted function defaults remain outside the trust model.

Only an exact lower private claim result returned by the pinned authentic
function authorizes execution. Arbitrary truthy values and lookalikes do not.
Phase 7.8 treats the claim as opaque and does not inspect its generation or
ownership provenance.

Before claim, the runner compares the exact built-in model string on the
bridged executor configuration with the model on the exact base runtime
executor configuration. The base composition is used only as the source of
runtime-owned model configuration; no lifecycle, lease, tracker, registry, or
claim provenance is reconstructed. The runtime owns the model. Temperature,
token limit, and stop controls remain owned and validated by the execution
configuration. The frozen SDK bridge independently rejects nonempty stop
sequences for this canonical smoke request, so they do not represent a
successful smoke configuration even though the generic execution model can
represent them.

## Revision 4 lower-owned registration claim

Revision 4 removes Phase 7.8's manual reconstruction of bridged and base
ownership provenance. After validating the exact open bridged composition,
executor, bridge client, callable authority, execution configuration, and SDK
bridge authority, the runner calls the verified lower-owned
`_claim_bridged_registration_authority(...)` exactly once. The lower runtime is
the sole authority for wrapper registration, base registration, lease, claim,
weak-reference, callback, tracker, and lifecycle provenance.

A rejected claim becomes the fixed dependency failure. Because ownership was
not handed off, Phase 7.8 does not guess cleanup and does not execute. A valid
claim authorizes one execution followed by exactly one bridged close on every
post-claim outcome. Close failure retains lifecycle precedence, and
`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` continue to follow the
verified lower-runtime policy.

Request construction and lineage, provider-result reconstruction and lineage,
strict `SMOKE_OK` interpretation, execution-configuration validation, model
coherence, bridge callable validation, error isolation, passive imports, and
the seven-symbol public API are unchanged. Phase 7.8 does not inspect bridged
registries or any wrapper/base ownership tracker.

## Revision 3 ownership-handoff correction

Revision 2 closed the executor and bridge authority gap, but execution authority
alone was insufficient: a copied-invalid base lifecycle could still be accepted
until cleanup, and a lifecycle from another composition could redirect cleanup
after successful execution. Revision 3 therefore treats the delegated base
composition and its ownership state as untrusted before handoff.

The runner reuses the verified Phase 7.7 base-composition validator rather than
defining a second lifecycle contract. That validator checks the exact open
lifecycle owner, cleanup callable and receiver, success and failure callbacks,
ownership lease, weak-reference coherence, ownership tracker record and LIVE
state, SDK client authority, raw client, and Responses provenance. The runner
additionally checks that the bridged wrapper identity equals the exact base
identity and that the frozen wrapper tracker contains the weak reference to the
same returned composition.

Execution lineage and cleanup lineage must be identical before ownership is
accepted. Malformed lifecycle, lease, tracker, raw cleanup, or cross-composition
ownership state is rejected as a fixed dependency failure before provider
execution, Responses invocation, or guessed cleanup. Request/result validation,
valid execution-configuration support, exact-once cleanup after valid handoff,
lifecycle precedence, and the documented BaseException policy are unchanged.

## Revision 2 handoff correction

Independent verification of Revision 1 found that exact outer composition and
executor types were insufficient: copied-invalid returned compositions could
replace the executor client, authorized callable, or receiver without being
rejected by the Phase 7.8 handoff validator. Revision 2 treats every returned
composition as untrusted until its complete execution authority is validated.

Before execution, the runner now validates the exact open composition, exact
executor and bridge client, client identity, authentic bridge `complete`
callable, invocation kind and receiver, strictly reconstructed execution
configuration with exact field preservation, SDK client authority, mapper and
SDK request-type generation, bridge-to-base SDK provenance, and the authentic
delegated base-close authority. Foreign clients, callables, receivers,
configurations, bridge generations, and cross-composition execution authority
are rejected before execution or cleanup ownership handoff. The runner does not
guess cleanup for malformed producer output. Legitimate Phase 7.7 Revision 9
compositions retain the same one-execution and one-close behavior; request,
result, lifecycle, and control-flow semantics are unchanged.

The focused regression suite now commits the original foreign-client,
foreign-callable, and foreign-receiver reproductions plus bridge-slot,
configuration, closed-state, simultaneous-mutation, and cross-composition
cases. This is defensive validation of returned public-boundary values, not a
claim of generic resistance to arbitrary hostile same-interpreter mutation
outside that boundary.

The bridged package name remains split into constant fragments because a frozen
lexical sentinel intended to prevent lower-layer reverse imports scans every
source file outside the bridged package, including authorized future higher
layers. The semantic dependency remains the documented upward Phase 7.8 →
Phase 7.7 dependency; no lower package imports Phase 7.8. The workaround reduces
static readability but does not reverse or bypass the architectural dependency
rule, and it is not expanded beyond this required import.

## Purpose and boundary

Revision 1 is a fully offline, live-shaped, end-to-end integration proof. It is
non-networked, non-CLI, and non-production. It does not contact OpenAI and must
not be described as a real live provider request.

The dependency direction is strictly upward:

```text
provider_v2
  ↑ provider_execution_v2
  ↑ provider_execution_openai_v2
  ↑ provider_execution_openai_sdk_v2
  ↑ provider_execution_openai_sdk_bridge_v2
  ↑ provider_runtime_openai_v2
  ↑ provider_runtime_openai_bridged_v2
  ↑ provider_smoke_request_authority_v2
  ↑ provider_runtime_openai_live_smoke_v2
```

No lower package depends on this integration package.

## Verified execution chain

```text
OpenAILiveSmokeConfigurationV2
  ↓ build_canonical_smoke_execution_plan()
SmokeExecutionPlanV2
  ↓ SmokeProviderExecutionRequestAuthorityV2.construct(...)
ProviderExecutionRequestV2
  ↓ OpenAIBridgedRuntimeComposerV2.compose()
OpenAIBridgedRuntimeCompositionV2
  ↓ OpenAIProviderExecutorV2.execute(request)
OpenAIExecutionSDKBridgeClientV2.complete(...)
  ↓ OpenAISDKClientV2.complete(...)
offline Responses capability
  ↓ ProviderExecutionResultV2
strict smoke-result interpretation
  ↓ OpenAILiveSmokeResultV2
  ↓ composition.close()
```

Phase 7.6 owns the canonical request. Phase 7.7 owns runtime assembly and
execution–SDK compatibility. The SDK boundary owns Responses request mapping.
The Phase 7.8 runner owns orchestration, strict result interpretation, and one
cleanup obligation after an exact bridged composition is handed off.

The runner never fabricates `ProviderExecutionResultV2`, provider output
authority, or an SDK response. `SMOKE_OK` must originate in the offline
Responses capability and traverse all verified lower boundaries. The runner
contains the expected comparison value only to interpret that authentic result.

## Configuration and confirmation

Configuration contains only:

- exact `confirm_live` boolean;
- caller-supplied, unpadded request ID;
- caller-supplied exact UTC timestamp;
- frozen-compatible positive finite timeout.

There is no hidden clock, random request ID, model, prompt, credential, retry,
or transport setting. `confirm_live=True` authorizes only the complete offline
live-shaped path. It does not authorize environment inspection, credential
retrieval, an official OpenAI client, networking, a real API request, or CLI
execution.

## Strict request and result authority

The returned request must be the exact `ProviderExecutionRequestV2`, survive
strict reconstruction, belong to the canonical OpenAI descriptor and plan,
contain exactly one canonical generation message, preserve caller identity,
UTC time, and timeout, and have uncancelled empty execution metadata.

A successful provider result must:

- be the exact `ProviderExecutionResultV2` and survive strict reconstruction;
- be `completed`, with neither execution failure field present;
- match request ID, provider ID, and request-envelope identity;
- contain a successful provider projection with no failure code;
- contain exactly one output at ordinal zero with matching source lineage;
- have completed finish semantics;
- contain exactly `SMOKE_OK`.

The runner does not trim, concatenate, normalize, case-fold, choose among
outputs, accept partial/content-filtered completion, or accept foreign lineage.

## Lifecycle and failure policy

Before valid composition handoff, the runner performs no guessed cleanup. After
handoff, `composition.close()` is invoked exactly once on success, execution
failure, malformed results, wrong text, lineage mismatch, interpretation
failure, and control-flow exceptions. There is no retry and no second close.

An ordinary close failure has lifecycle precedence over an ordinary execution
or validation failure. A cleanup `KeyboardInterrupt`, `SystemExit`, or
`GeneratorExit` propagates as the same control-flow exception. With successful
cleanup, an execution control-flow exception also propagates unchanged. Runner
frames clear dependency-bearing references before public fixed errors are
created; dependency-owned frames are not claimed to be sanitized by this layer.

Public ordinary errors have fixed messages, no chained cause or context, and do
not expose raw lower diagnostics or per-run objects.

## Passive and explicit behavior

Passive import does not load the official OpenAI package or SDK implementation,
load bridge bootstrap, inspect OpenAI/Azure environment state, construct a
request or runtime, execute a provider, or perform network/process/thread work.

An explicit offline run may transitively load the already verified SDK boundary
and bridge bootstrap. Tests supply only a synthetic offline credential through
the verified lower test-safe composition. No environment credential source,
official live client, or network operation is used.

## Trust model and deferred work

Trusted authority consists of verified lower packages at module initialization,
exact injected bridged composer and request authority types, pinned exact
project-owned callables, and defensively reconstructed configuration. Returned
requests, compositions, provider results, nested outputs, copied-invalid models,
and ordinary exceptions are untrusted.

Compromised import hooks, `sys.modules` substitution, hostile mutation before
trusted-module initialization, direct private-slot mutation, and debugger or
memory instrumentation are outside the trust model. Private naming is not an
access-control mechanism.

Revision 2 is reserved for production dependency assembly. A later separately
authorized revision may perform one real OpenAI smoke request. Revision 1 does
not wire the CLI.
