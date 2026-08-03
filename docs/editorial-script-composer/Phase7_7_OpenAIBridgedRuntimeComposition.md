# Module 2.9 Phase 7.7 Revision 7 — Higher OpenAI Bridged Runtime Composition

Status: implemented, awaiting independent verification.

## Compatibility Revision 6 base-claim lineage

Base-claim evidence is now resolved registry-first.  The bridged authority binds
the exact base composition, authoritative base generation, authoritative base
registration record, and original base claim captured immediately after the
lower-owned atomic claim.  A later bridged claim first resolves the exact base
registration from that base composition and requires its `CLAIMED` generation
and record identities to match before accepting either stored bridged claim
binding.  Coordinated foreign-claim replacement and exact-type claims carrying
foreign generations therefore cannot authenticate.  The base runtime remains
unchanged; local deep lifecycle and configuration checks remain supplemental
compatibility validation rather than the provenance root.

## Compatibility Revision 5 registration provenance

Wrapper ownership now uses a private, process-local generation authority rather
than treating `_LIVE_WRAPPERS` as sufficient proof. Each published wrapper is
bound to a fresh opaque `object()` generation, a sealed authority containing
the verified base-runtime claim and exact weakref/callback provenance, an
authoritative generation record, and a target-ID index. `_LIVE_WRAPPERS`
remains only as a compatibility projection.

The private keyword-only bridged claim validates the complete wrapper,
executor, bridge, base-composition, generation, callback, index, and
compatibility graph before atomically changing `LIVE` to `CLAIMED`. Base
ownership is claimed during bridged construction through the verified
base-runtime claim API; the bridged layer no longer reconstructs the base
tracker as its trust root. Successful close removes bridged registration state.
Ordinary and BaseException cleanup failures retain an exact
`TERMINAL_FAILED` tombstone, so cleanup cannot be retried. Weakref callbacks
remove only an exact dead registration and cannot remove a live target or a
newer generation. These guarantees are process-local and assume the existing
single-threaded composition contract.

## Revision 8 authority correction

Revision 7 independent verification found that outer exact types alone did not
reject copied-invalid SDK capability and lifecycle state. Revision 8 therefore
deeply validates the frozen base authority graph before live-wrapper
registration: the narrow SDK client and capability, pinned Responses callable
and receiver, base executor callable/client/configuration, lifecycle raw close
callable and receiver, transition callbacks and ownership lease, lower ownership
record, and the identity relationship between the Responses receiver and the raw
resource closed by the lifecycle owner.

The validation mirrors frozen lower-layer static authority helpers and never
invokes a descriptor, provider callable, cleanup callback, or release callback.
Malformed values are dependency failures before ownership handoff, bridge
bootstrap, executor construction, or rollback; cleanup is not guessed for an
invalid base result. A legitimate Phase 7.4 composition remains accepted. No
lower contract was modified.

This boundary defensively rejects copied-invalid and malformed values presented
to it. It does not claim generic tamper resistance against arbitrary hostile
same-interpreter mutation after successful validation.

## Revision 9 configuration compatibility correction

Revision 8 incorrectly narrowed the frozen execution configuration to default
temperature, output-token, and stop-sequence values. Revision 9 removes that
invented policy. The higher validator now requires exact field types, strict
defensive `OpenAIExecutionConfigV2` reconstruction, preservation of every
reconstructed field, and exact model coherence with `OpenAIRuntimeConfigV2`.
It accepts every temperature, output-token limit, and stop-sequence tuple valid
under the frozen lower contract while continuing to reject copied-invalid
state.

Stop sequences belong to execution-request policy. A valid configured tuple is
therefore accepted during runtime composition. The execution–SDK bridge remains
the frozen owner of rejecting a concrete request containing unsupported
nonempty stop sequences; composition does not predict the outcome of every
future request. Revision 8 deep SDK, executor, lifecycle, lease, tracker, and
execution/cleanup provenance validation remains unchanged.

## Architecture

This offline higher layer connects the verified `OpenAIRuntimeComposerV2` to
the verified execution–SDK bridge. The lower runtime remains unchanged and is
still the sole owner of credential retrieval, raw SDK construction, and raw
client lifecycle.

Dependency direction is strictly upward:

```text
provider_execution_openai_v2
    ↑ provider_execution_openai_sdk_v2
    ↑ provider_execution_openai_sdk_bridge_v2
    ↑ provider_runtime_openai_v2
    ↑ provider_runtime_openai_bridged_v2
```

Passive imports do not load `openai`, the SDK package, or the private bridge
bootstrap and perform no environment inspection. Explicit `compose()` calls the
pinned authentic base composer exactly once, validates the exact resulting base
composition, reserves unique live wrapping by object identity, explicitly
loads the atomic bridge bootstrap, constructs one exact bridge and one exact
`OpenAIProviderExecutorV2`, and returns the higher composition. It performs no
provider execution.

## Authority and lifecycle

The higher composer accepts only one exact `OpenAIRuntimeComposerV2`. Its
authentic `compose` function is pinned at trusted passive initialization;
descriptors, wrappers, subclasses, and later replacement cannot redirect it.
Mutation before trusted module initialization remains outside the same-process
identity contract.

The returned wrapper exposes only `executor`, `closed`, and `close()`. The exact
base composition remains the lifecycle delegate. The wrapper marks itself
closed before invoking the pinned base close function, invokes it at most once,
and never retries failed cleanup. Assembly failures after ownership handoff roll
back through that same base composition. Rollback failure takes lifecycle-error
precedence.

Only one live wrapper may own a given base composition identity. A private
tracker stores `id(base)` and a weak reference to the higher wrapper—not the
base, SDK client, bridge, executor, credential, or transport. Closing or
garbage-collecting the wrapper removes the registration. A duplicate live
wrapping attempt is rejected without closing the first wrapper's base.

Ordinary errors have fixed text and suppress context and cause. BaseExceptions
propagate after required rollback where ownership exists. An ordinary rollback
failure does not convert the original BaseException; a rollback BaseException
itself takes precedence, and registration release still occurs. Dependency-owned
tracebacks and fixed callable/class anchors remain visible under ordinary
same-interpreter inspection; the layer does not claim traceback secrecy against
debuggers or hostile private mutation.

Revision 7 constructs no official OpenAI client itself, retrieves no credential
separately, performs no network operation, and owns no raw lifecycle. Phase 7.8
is reserved for separately authorized offline live-smoke integration followed
by an explicitly authorized live invocation.
