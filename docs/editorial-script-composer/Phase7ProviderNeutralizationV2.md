# Phase 7.1 — Provider Neutralization V2, Revision 2

## Status and frozen boundary

Phase 7.1 adds a parallel V2 provider architecture. Phases 4.1 through 6.3 remain
unchanged and authoritative. V2 does not replace, wrap, migrate, re-export, or
modify their public models, builders, validators, identities, fingerprints,
references, serialization, or behavior.

No provider SDK, network call, authentication, timeout, retry, streaming, or model
selection is implemented.

## Package boundaries and runtime isolation

V2 deliberately lives outside `pastila_scout.editor.script_composer`. Importing a
subpackage executes its parent initializer, and the frozen Script Composer parent
exports OpenAI V1. Placing generic V2 beneath that parent would therefore violate
runtime isolation even without a direct source import.

```text
pastila_scout.provider_v2
    generic models, canonical authority, builders, validators, interface, registry

pastila_scout.provider_adapters_v2.<provider>
    one independently importable concrete adapter

pastila_scout.provider_composition_v2
    sole four-provider composition root
```

The generic package imports no Script Composer or adapter module. The adapter
package initializer imports no adapters. Importing one provider module therefore
loads only that provider. Importing the composition root intentionally loads all
four.

## Authority flow

```text
ProviderRequestIntentV2
    + validated ProviderDescriptorV2
    ↓ build_provider_request_envelope
ProviderRequestEnvelopeV2
    ↓ adapter-owned execution/extraction boundary
ProviderResultProjectionV2
    ↓ build_provider_result_envelope
ProviderResultEnvelopeV2
    ↓
future provider-neutral Composer
```

Builders reconstruct immutable inputs, derive canonical references, derive every
nested and aggregate identity, and then derive every fingerprint. Validators
reconstruct the submitted artifact and rebuild expected authority from the
original intent or result projection. Correctly resealed semantic substitutions
therefore remain invalid against unchanged authority.

Diagnostics are immutable, bounded, deterministically ordered
`ProviderV2ValidationIssue` objects.

## Registry authority

`ProviderRegistry` is immutable after construction and is the sole provider
gateway. Registration validates:

- canonical provider identifier;
- runtime `ProviderAdapter` conformance;
- required lifecycle methods and metadata;
- provider ownership;
- adapter identity ownership;
- descriptor structure, version, identity, and fingerprint;
- duplicate provider ownership.

Resolution rejects invalid and unknown identifiers. The mapping is read-only and
there is no mutable singleton, runtime registration, or lazy mutation.

## Provider-neutral envelopes

The request envelope contains ordered provider-neutral roles and content plus
execution/draft lineage. It contains no concrete request DTO.

The result envelope contains ordered neutral output units with:

- generated UTF-8 text;
- provider-neutral finish reason;
- status and failure code;
- exact request-unit lineage;
- deterministic identities and fingerprints.

It contains no provider identifier, provider DTO, SDK object, Phase 6.2 object, or
Phase 6.3 object. A future Composer can consume `outputs` directly without
resolving or recognizing the originating provider.

## Adapter lifecycle

`ProviderAdapter` defines metadata, request construction, request validation,
execution, response extraction, result projection, and result validation.

OpenAI is the reference adapter. Its existing V1 authority remains exposed as the
exact frozen callable objects; no compatibility wrapper changes semantics. Its V2
neutral lifecycle uses the authoritative V2 builders and validators. Execution
raises the controlled unavailable error because provider transport is excluded
from this phase.

Claude, Gemini, and Ollama implement the same lifecycle through the shared adapter
base while deliberately providing no execution, transport, credentials, retries,
or SDK integration.

## Composition root

`pastila_scout.provider_composition_v2` is the only module that imports and wires
all concrete providers. It constructs a new immutable registry containing exactly
OpenAI, Claude, Gemini, and Ollama. The future GUI needs only the provider ID and
display name for its single **AI Provider** selector.

## Future provider onboarding

A future provider such as Mistral requires only:

1. one independent adapter module implementing `ProviderAdapter`;
2. one canonically sealed descriptor;
3. registration in the application composition root.

The generic core, Editor, Prompt Rendering, frozen execution authority, envelopes,
and future Composer contract remain unchanged.

## Remaining intentional limitations

Phase 7.1 does not perform provider execution. It does not define SDK payloads,
transport DTOs, credentials, retries, caching, streaming, or GUI behavior. These
remain provider-owned future concerns and cannot enter the generic envelope.

## Revision 3 corrective authority

Revision 3 hardens registry composition by comparing every adapter lifecycle
callable with the authoritative `ProviderAdapter` signature. Missing or extra
required arguments, incompatible positional or keyword-only structure, and
contradictory annotations are rejected deterministically without invoking the
adapter.

Result projections and envelopes now share one semantic invariant. Successful
results require completed outputs and no failure code; failed results require a
failure code and no output; partial results require a failure code and genuinely
partial output rather than a wholly completed or wholly failed set. Content-filtered
output is therefore never authoritative top-level success.

Focused adversarial regressions cover callable lifecycle impostors, bound and
unannotated valid adapters, status/finish contradictions, correctly resealed
contradictory envelopes, deterministic diagnostics, and input immutability. No
provider execution or frozen Phase 4.1 through 6.3 behavior changed.

## Revision 4 static lifecycle authority

Revision 4 resolves lifecycle members with `inspect.getattr_static` and accepts
only genuine Python instance methods or signature-compatible `staticmethod` and
`classmethod` declarations. Static methods are compared as declared; class methods
discard their bound class receiver before comparison, matching caller-visible
behavior.

Properties, cached properties, arbitrary descriptors, callable instance
attributes, dynamically manufactured members, and custom `__getattribute__`
interception are rejected. Registry composition does not execute descriptor
binding, dynamic lookup hooks, or lifecycle method bodies. Adversarial tests use
explicit counters to prove these operations remain side-effect free and produce
deterministic errors.

This correction changes no result semantics, provider execution behavior, public
exports, import boundaries, or frozen Phase 4.1 through 6.3 authority.

## Revision 5 callable and abstract authority

Revision 5 derives lifecycle signatures from a metadata-free clone of the actual
Python function code. Signature validation therefore neither follows copied
`__wrapped__` metadata nor trusts a forged `__signature__`. Compatible decorated
wrappers remain valid when their real wrapper accepts the authoritative arguments;
copied metadata cannot legitimize a missing, extra, or keyword-only argument.
Annotations copied through `__wrapped__` are not treated as annotations owned by
the wrapper itself.

Any lifecycle representation marked `__isabstractmethod__` is rejected, including
instance, static, class, inherited, overridden, and decorated methods. A concrete
compatible override of an abstract base implementation remains valid.

Focused adversarial tests cover compatible and incompatible wrappers, variadic
wrappers, forged signature metadata, static and class method decorators, structural
abstract methods, inheritance transitions, deterministic diagnostics, and zero
lifecycle-body execution. No provider execution, result semantics, public API,
import boundary, or frozen Phase 4.1 through 6.3 behavior changed.

## Revision 6 static annotation authority

Revision 6 reads annotations only from the actual Python function's own static
`__annotations__` mapping and copies that mapping before validation. Neither
`__wrapped__` nor `__signature__` contributes callable or annotation authority.
The registry does not use `typing.get_type_hints`, evaluate annotation strings,
or resolve names through adapter globals.

A narrow AST classifier resolves only trusted generic-core contract names, safe
built-ins, `Any`, `None`, explicitly trusted qualified names, safe unions, and
safe built-in generic forms. Unknown names are unresolved; calls, lambdas,
comprehensions, arbitrary attributes or subscripts, imports, conditionals, and
other executable expressions are rejected deterministically without evaluation.
On Python 3.14, deferred annotator bytecode is screened against a closed opcode
and trusted-global allowlist before string-form syntax is requested; call-bearing
or dynamically resolving annotators are rejected before they can run.
Unannotated implementations remain valid, while compatible concrete, `Any`,
contravariant `object`, and safe forward-reference annotations retain their
existing compatibility behavior.

Adversarial tests prove wrapper metadata cannot suppress invalid annotations and
that annotation factories, module lookup hooks, wrapper bodies, and lifecycle
bodies remain unexecuted. This correction changes no provider execution, result
semantics, public API, import boundary, identity, fingerprint, or frozen behavior.

## Revision 7 registry-owned annotation authority

Revision 7 separates adapter-supplied annotation syntax from annotation symbol
authority. Every accepted name and the sole qualified name `typing.Any` resolves
through immutable registry-owned tables. Adapter globals, builtins, closure cells,
defaults, imported modules, and dynamic attributes contribute no annotation
objects.

Python 3.14 deferred annotators are opcode-screened and cloned with sanitized
trusted globals, empty builtins, and a sanitized class-namespace closure. The
original annotator is never invoked. Calls, arbitrary attributes, unknown globals,
and non-class closure variables are rejected before the sanitized clone runs.
Trusted unions and built-in generics are therefore constructed only from exact
registry-owned objects.

Already resolved annotations are accepted only by trusted identity or as exact
built-in generic aliases and union objects recursively composed of trusted values.
Arbitrary classes, hostile metaclasses, and custom objects are rejected before
equality, hashing, representation, subtype, union, or subscription behavior can
run. Hostile global, builtin, closure, resolved-object, union, and generic tests
assert zero special-method and lifecycle execution. No provider execution, result
semantics, public API, import boundary, or frozen behavior changed.

## Revision 8 deferred-annotation non-execution

Revision 8 removes sanitized deferred-annotator execution. Sanitized globals were
insufficient because a code object can contain an opaque object constant that an
otherwise ordinary bytecode operation could use. Registry validation therefore
never invokes lifecycle `__annotate__` functions, clones their code, interprets
their constants, or attempts a fallback annotation format.

A lifecycle function with non-null deferred annotation machinery is rejected with
the stable `deferred annotations require execution` diagnostic. A genuinely
unannotated function has no annotator and remains valid. A function may also
publish an explicit concrete `__annotations__` dictionary; that mapping is copied
and validated through the existing registry-owned name tables and trusted resolved
object normalization. The shared registry-owned adapter base publishes such
materialized mappings explicitly so the four default providers remain compatible
without annotation-bytecode execution.

This change preserves the Revision 7 symbol-authority boundary, safe static string
parsing, trusted union and generic handling, lifecycle shape checks, result
semantics, provider neutrality, public exports, and frozen V1 delegation. It adds
no provider execution or other runtime integration.
