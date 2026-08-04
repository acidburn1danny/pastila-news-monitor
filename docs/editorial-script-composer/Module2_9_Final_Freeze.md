# Module 2.9 Final Freeze

Status: **FROZEN BASELINE — awaiting independent verification of this freeze package**

Verified implementation tag: `module-2.9-phase-7.8-r6-verified`  
Verified implementation commit: `26f22b128b37822501636bc57294f05f0a9aac87`

## Objective

Module 2.9 provides the provider-neutral execution architecture and its verified
OpenAI implementation: provider-neutral request and result boundaries,
registration provenance, claim authority, producing-runtime configuration
authority, and an offline live-shaped smoke integration. It does not itself
authorize a production provider rollout.

## Final architecture

Every arrow below points from a **consumer** to a **dependency**:

```text
provider_execution_v2 ────────────────────────────────> provider_v2
provider_execution_openai_v2 ────────────────────────> provider_execution_v2
provider_execution_openai_v2 ────────────────────────> provider_v2

provider_execution_openai_sdk_v2 ────────────────────> provider_execution_openai_v2
provider_execution_openai_sdk_bridge_v2 ─────────────> provider_execution_openai_v2
provider_execution_openai_sdk_bridge_v2
  └─ explicit operational bootstrap only ────────────> provider_execution_openai_sdk_v2
provider_runtime_openai_v2 ──────────────────────────> provider_execution_openai_sdk_v2
provider_runtime_openai_v2 ──────────────────────────> provider_execution_openai_v2

provider_runtime_openai_bridged_v2 ──────────────────> provider_runtime_openai_v2
provider_runtime_openai_bridged_v2 ──────────────────> provider_execution_openai_sdk_bridge_v2
provider_runtime_openai_live_smoke_v2 ───────────────> provider_runtime_openai_bridged_v2
provider_runtime_openai_live_smoke_v2 ───────────────> provider_smoke_request_authority_v2
```

`provider_smoke_request_authority_v2` builds the canonical provider-neutral
smoke plan and execution request consumed by the live-smoke boundary.
`provider_runtime_openai_smoke_v2` is the earlier injected smoke-test contract;
it is separate from the final live-shaped offline integration. No lower package
imports either higher smoke consumer.

The SDK bridge is an execution bridge and a sibling of the base runtime, not a
parent in a runtime inheritance chain. Its passive package boundary consumes the
OpenAI execution contract. Only its explicit operational bootstrap resolves the
frozen SDK adapter. The bridged runtime consumes both this bridge and the base
runtime and composes their independently owned responsibilities.

## Verified milestones

| Tag | Commit | Purpose | Status |
|---|---|---|---|
| `module-2.9-phase-7.3-frozen` | `24e2eb163b4d0fac485c70f7efb1d6c934a6ba79` | Frozen operational SDK adapter boundary | Frozen |
| `module-2.9-phase-7.4-r5-verified` | `fa0e8c81f4f9cf8eab1dfead51ba43ffeb1604a7` | Runtime composition boundary | Verified |
| `module-2.9-phase-7.4-r8-verified` | `af60ee90dda35e417d72663460440b5ed8874e0c` | Operational runtime composition | Verified |
| `module-2.9-phase-7.4-r11-verified` | `a58603bdd6f5f20a02c5c9a3a259ca39a173b238` | Concrete runtime dependencies | Verified |
| `module-2.9-phase-7.4-r12-verified` | `7933644125552d5f7dbfd39781b086c5846b5042` | Environment credential adapter | Verified |
| `module-2.9-phase-7.5-r2-verified` | `3e1372cce6d7defee8cbc7e90dc2eeee503588c5` | Non-operational smoke boundary | Verified |
| `module-2.9-phase-7.5-r4-verified` | `426087b7407eb4dd45f544d6b902675ec8ad4fc6` | Hardened smoke boundary | Verified |
| `module-2.9-phase-7.6-r1-verified` | `ffa02e87285388baecae5672ecadbbc3eb21a21d` | Canonical smoke request authority | Verified |
| `module-2.9-phase-7.6-r2-verified` | `31009b3ef66a4d5ffaa8c8d0566cc69c1ebd7a28` | Canonical execution request construction | Verified |
| `module-2.9-phase-7.7-r6-verified` | `4d9036617f043208377f62db35f62657a43aec18` | Execution–SDK bridge | Verified |
| `module-2.9-phase-7.7-r9-verified` | `d360adb7ec569bb3d0af6b3330e32f279e4ff98d` | Bridged runtime composition | Verified |
| `module-2.9-phase-7.7-compat-r4-verified` | `880d8dad00185a2b44a82d28627359c0c664184e` | Base registration provenance | Verified |
| `module-2.9-phase-7.7-compat-r6-verified` | `e871af89cf49f1bcd71a7b6c186818de98633f34` | Bridged registration and base-claim provenance | Verified |
| `module-2.9-phase-7.8-r6-verified` | `26f22b128b37822501636bc57294f05f0a9aac87` | Offline live-smoke integration and producing-model authority | Verified |

## Trust model

| Authority | Owner / producer | Consumer | Validation rule | Must not be reconstructed by |
|---|---|---|---|---|
| Provider identity | `provider_v2` registry | Execution layers | Exact registered descriptor identity | SDK/runtime consumers |
| Request authority | Smoke request authority | Live-smoke runner | Exact canonical plan and request reconstruction | Runtime or provider result |
| Execution lineage | `provider_execution_v2` | Provider executor | Exact request/envelope identity and fingerprint | SDK response mapper |
| Base registration provenance | Base runtime | Bridged runtime | Registry-first exact generation, record, state, target | Higher smoke runner |
| Wrapper registration provenance | Bridged runtime | Live-smoke runner | Exact lower-owned atomic claim | Higher smoke runner |
| Base claim authority | Base runtime | Bridged runtime | Original claim bound independently to authoritative generation | Stored bridged claim copies |
| Bridged claim authority | Bridged runtime | Live-smoke runner | Exact pinned callable and exact opaque result type | Phase 7.8 provenance logic |
| Claim callable authority | Clean Phase 7.8 initialization | Runner instance | Exact identity pinned into immutable slot | Names/signatures/wrappers |
| Producing configuration | Exact base runtime composer | Runner instance | Exact validated model captured once, then three-way coherence | Mutable executor projections |
| Provider result lineage | Provider executor/result contracts | Live-smoke runner | Strict reconstruction and exact request/provider/envelope coherence | Raw SDK response |
| Lifecycle ownership | Base and bridged runtime owners | Higher composition | Exact-once handoff and terminal state machine | Callers or result interpreters |

## Lifecycle model

The base runtime owns raw-client cleanup. The bridged runtime owns wrapper
cleanup and delegates exactly once to the base owner. Atomic claims transition
registrations from `LIVE` to `CLAIMED`. Cleanup failure transitions ownership to
`TERMINAL_FAILED`; it retains the provenance tombstone and forbids retry.
Successful close and exact wrapper garbage collection remove registrations and
claim bindings. Generation and callback identity prevent stale callbacks from
removing newer registrations. Cleanup BaseExceptions preserve the verified
precedence and identity rules.

## Import passivity

Import behavior is package-specific. “Environment inspection” below means an
environment lookup performed by the imported third-party SDK; it does not mean
that this project deliberately requests, stores, logs, or exposes the value.

| Package | Official `openai` loaded | OpenAI/Azure environment inspection | Official client construction | Runtime composition | Provider execution | Networking | Threads | Subprocesses | stdout | stderr | Warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `provider_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_adapters_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_execution_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_execution_testing_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_execution_openai_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_execution_openai_sdk_v2` | Yes | Yes, by third-party SDK initialization | No | No | No | No | No | No | Empty | Empty | None |
| `provider_execution_openai_sdk_bridge_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_runtime_openai_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_runtime_openai_smoke_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_smoke_request_authority_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_runtime_openai_bridged_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |
| `provider_runtime_openai_live_smoke_v2` | No | No | No | No | No | No | No | No | Empty | Empty | None |

Passive import of `provider_execution_openai_sdk_v2` imports official OpenAI
SDK definitions. During its own initialization, that third-party SDK may inspect
OpenAI/Azure environment settings such as logging, API-type/version, endpoint,
or Azure token variables. No official client is constructed, no provider is
executed, and no network request occurs. Project code does not intentionally
retrieve or retain credential values during this package import.

For every package other than the SDK adapter, the table records the stronger
passive-import result across each independently reported dimension. Explicit
bridge bootstrap and explicit runtime composition are operational boundaries,
but neither runs during passive package import.

## Public APIs

### `provider_execution_openai_sdk_v2`

```text
OpenAISDKBoundaryError, OpenAISDKCapabilityV2, OpenAISDKClientV2,
OpenAISDKConfigurationError, OpenAISDKDependencyError, OpenAISDKRequestV2,
OpenAISDKResponseError, build_openai_sdk_request,
classify_openai_sdk_exception, reconstruct_openai_sdk_response
```

### `provider_runtime_openai_v2`

```text
OpenAICredentialSourceV2, OpenAIRuntimeComposerV2,
OpenAIRuntimeCompositionError, OpenAIRuntimeCompositionV2,
OpenAIRuntimeConfigV2, OpenAIRuntimeConfigurationError,
OpenAIRuntimeCredentialError, OpenAIRuntimeDependencyError,
OpenAIRuntimeLifecycleError, OpenAIRuntimeLifecycleV2, OpenAISDKFactoryV2
```

### `provider_runtime_openai_smoke_v2`

```text
OpenAISmokeTestConfigurationError, OpenAISmokeTestConfigurationV2,
OpenAISmokeTestConfirmationError, OpenAISmokeTestDependencyError,
OpenAISmokeTestError, OpenAISmokeTestResultV2, OpenAISmokeTestRunnerV2
```

### `provider_smoke_request_authority_v2`

```text
SmokeExecutionPlanV2, SmokeExecutionRequestAuthorityError,
SmokeExecutionRequestConfigurationError, SmokeExecutionRequestDependencyError,
SmokeProviderExecutionRequestAuthorityV2, build_canonical_smoke_execution_plan
```

### `provider_execution_openai_sdk_bridge_v2`

```text
OpenAIExecutionSDKBridgeClientV2, OpenAIExecutionSDKBridgeError,
OpenAIExecutionSDKBridgeConfigurationError,
OpenAIExecutionSDKBridgeDependencyError
```

### `provider_runtime_openai_bridged_v2`

```text
OpenAIBridgedRuntimeComposerV2, OpenAIBridgedRuntimeCompositionV2,
OpenAIBridgedRuntimeError, OpenAIBridgedRuntimeConfigurationError,
OpenAIBridgedRuntimeDependencyError, OpenAIBridgedRuntimeLifecycleError
```

### `provider_runtime_openai_live_smoke_v2`

```text
OpenAILiveSmokeRunnerV2, OpenAILiveSmokeConfigurationV2,
OpenAILiveSmokeResultV2, OpenAILiveSmokeError,
OpenAILiveSmokeConfigurationError, OpenAILiveSmokeDependencyError,
OpenAILiveSmokeLifecycleError
```

## Verified behavior

The frozen baseline enforces exact types, strict reconstruction, provider
identity coherence, request/result lineage, no silent fallback, zero retries
unless explicitly owned by a lower contract, exact-once execution and close,
lower-owned provenance rather than higher-layer reconstruction, exact
`SMOKE_OK`, passive imports, sanitized public errors, and the established
BaseException propagation policy.

## Explicit non-goals

This freeze does not provide application-level provider-neutral rollout,
CLI/GUI provider selection, Ollama, Gemini or Claude runtimes, live production
provider execution, automatic fallback, multi-provider routing, load balancing,
streaming, persistence, or telemetry.

## Threat-model boundaries

In scope are copied-invalid exact instances, ordinary post-initialization
callable and descriptor substitution, foreign lineage donation, coordinated
weak-reference/callback substitution, cleanup retry, stale callbacks, and the
documented coordinated mutable-projection attacks.

Out of scope are hostile mutation before a specifically documented trusted
import boundary, compromised import hooks or `sys.modules`, direct debugger or
memory manipulation, direct mutation of explicitly private trusted anchors or
slots, and code-object mutation. Python private state is not represented as an
external security boundary.

## Change control

Any future modification to frozen Module 2.9 production code requires:

1. an explicit compatibility revision;
2. narrowly defined scope;
3. independent verification;
4. an updated integrity manifest;
5. a new verified tag.

Frozen production code must not receive silent in-place behavioral edits.
