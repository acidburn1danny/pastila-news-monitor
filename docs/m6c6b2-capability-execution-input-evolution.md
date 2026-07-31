# M6C.6B.2 Capability Execution Input Evolution

## Transport architecture

M6C.6B.2 transports the exact immutable M6C.6A.1 planning input into an
executor-request v2 envelope. Dispatch remains capability-neutral: it validates
versions, action, capability, descriptor compatibility, fingerprints, lineage,
and identity, but never reads revision policy, scope, instructions, targets, or
source-draft meaning.

`CorrectiveActionExecutorRequestV2` contains the exact version-2 planning result,
its exact planning input, and an exact legacy executor request. The legacy request
continues to own plan, descriptor, execution context, authorization validation,
and all version-1 semantics. No execution-input copy exists.

The dispatcher-owned pure construction function builds and validates the legacy
request from the v2 result's exact legacy result, then wraps it with the unchanged
planning input. Lineage is planning result v2 → planning input → executor request
v2. Nested Draft Revision policy, scope, instructions, and source draft preserve
identity automatically because the generic transport never reconstructs them.

## Compatibility

Version-1 `CorrectiveActionExecutorRequest` is untouched. Its constructor,
validation, serialization, and fingerprint payload remain bit-for-bit identical.
Version 2 uses composition rather than a nullable legacy field. Unknown versions,
action/capability mismatches, descriptor mismatch, planning-result mismatch, and
input identity mismatch fail closed without falling back to v1.

Safe reports contain only controlled metadata and fingerprints. They exclude
draft prose, editorial instructions, prompts, provider information, and runtime
objects.

## Ownership and limitations

This milestone deliberately stops at executor-request construction. Full v2
dispatcher invocation would also require versioned dispatch-result and
executor-result return transport, which is not needed until a v2 capability
executor exists and was not authorized here. Existing dispatcher execution,
bindings, resolution, and result behavior remain frozen.

M6C.6D Part 2 can now resolve every planning-owned revision input from one
`CorrectiveActionExecutorRequestV2`. Controlled Generation still lacks a targeted
revision request and remains a separate compatibility evolution.
