# Phase 4.2 — Editor Request Fingerprint Authority Specification V1

Status: **normative specification — ready for independent implementation-readiness review**

Baseline: `phase-4.2-editor-generation-authority-r3b-verified` / `bcd6d804d894b0dcef7419060a172732aa9543fa`

## 1. Scope and normative language

The words **MUST**, **MUST NOT**, **SHALL**, and **SHALL NOT** are normative.
This document specifies one additive public fingerprint authority. It does not
change or implement Revision 3B, provider execution, runtime composition,
generation, retry, persistence, CLI, Producer, or GUI behavior.

## 2. Inspected repository architecture

The frozen `EditorGenerationApplicationRequestV1` has ten public fields. The
first nine are semantic inputs; `request_fingerprint` is the tenth. Its
constructor requires the caller to supply that fingerprint and validates it
against a privately calculated expected value.

Current generation-request fingerprint code is confined to
`editor_generation_authority_v1`:

- `canonical.py` defines `canonical_value`, `canonical_json`,
  `semantic_fingerprint`, and `tagged_number`;
- `models.py` defines private `_request_semantics`, `_options_semantics`, and
  `_option_values`;
- `EditorGenerationApplicationRequestV1._initialize` hashes the private request
  semantics and rejects a mismatching supplied fingerprint; and
- `EditorGenerationRequestAuthorityV1.build` consumes an already constructed
  application request and binds its fingerprint into the lower application
  reference.

Although `canonical.py` declares its own module `__all__`, none of those names
is exported by the package public API. The semantic payload builders are
underscore-private. No public generation fingerprint factory or authority
exists. Other repository fingerprint functions belong to different domains,
including Provider V2 envelopes and Editor artifacts, and do not accept this
request payload. They are not substitutes.

Consequently a caller can construct the frozen request only by duplicating the
algorithm or importing private helpers. Both violate the verified dependency
boundary. This is the public API gap addressed here.

## 3. Singular ownership

`EditorRequestFingerprintAuthorityV1` is the sole public owner of:

- canonical serialization for generation application-request fingerprints;
- deterministic request-fingerprint construction;
- validation of a supplied fingerprint against reconstructed semantics; and
- fingerprint reconstruction from the complete semantic inputs.

It owns no application request identity/reference, provider descriptor,
provider selection or execution, schema construction, timeout or cancellation
policy, retry, runtime, persistence, execution coordination, or output lineage.
It reads already-authoritative values and returns one lowercase SHA-256 string.

The package-private Revision 3C application-request construction boundary calls
this authority exactly once, then passes the returned value to
`EditorGenerationApplicationRequestV1`. A `LanguageModelProvider` adapter MUST
NOT calculate, validate, or reconstruct a request fingerprint directly; it
delegates request assembly to that exact builder.

## 4. Exact additive package

Future implementation creates exactly:

```text
src/pastila_scout/editor_request_fingerprint_authority_v1/
    __init__.py
    authority.py
    errors.py
```

There is no models, canonical, registry, factory, composition, provider, or
runtime module. The exact ordered package API is:

```python
__all__ = (
    "EditorRequestFingerprintAuthorityError",
    "EditorRequestFingerprintAuthorityV1",
)
```

No helper, payload, provider type, SDK type, runtime type, CLI type, or private
Revision 3B symbol is exported.

## 5. Exact semantic inputs

Both public methods accept the same keyword-only semantic inputs, in this exact
order:

```python
provider: ProviderChoiceV1
prompt: str
request_reference: str
requested_at: datetime
options: EditorGenerationRuntimeOptionsV1
output_schema_name: str
output_schema_canonical_json: str
output_schema_fingerprint: str
cancellation: CancellationTokenV2
```

These are exactly the nine fields preceding `request_fingerprint` in the
frozen request. The authority reconstructs exact public contract types using
their public copy/validation behavior. It rejects subclasses, coercion,
copied-invalid values, non-aware time, invalid text, noncanonical schema JSON,
schema-fingerprint mismatch, provider/options mismatch, and unsupported option
state exactly as the frozen request does.

Every input participates. Nothing else participates. In particular, runtime
reference/fingerprint, execution request, deterministic Editor artifacts,
process identity, environment, credentials, current clock, random value,
filesystem state, provider descriptor, lower envelope, and output are excluded.

## 6. Canonical semantic payload

The authority reconstructs this exact mapping before serialization:

```python
{
    "provider": provider.value,
    "prompt": prompt,
    "request_reference": request_reference,
    "requested_at": requested_at,
    "options": {
        "provider": options.provider.value,
        "model_identifier": options.model_identifier,
        "model_revision": options.model_revision,
        "temperature": tagged_number(options.temperature),
        "top_p": tagged_number(options.top_p),
        "max_output_tokens": options.max_output_tokens,
        "seed": options.seed,
        "stop_sequences": options.stop_sequences,
        "structured_output_mode": options.structured_output_mode,
        "timeout_seconds": tagged_number(
            options.timeout_policy.timeout_seconds
        ),
    },
    "output_schema_name": output_schema_name,
    "output_schema_canonical_json": output_schema_canonical_json,
    "output_schema_fingerprint": output_schema_fingerprint,
    "cancellation_requested": cancellation.cancellation_requested,
}
```

Provider and model participate through provider, identifier, revision, and
options provider. Temperature, top-p, maximum tokens, seed, stop absence,
structured-output mode, timeout, and cancellation participate exactly.
Structured-output authority participates through the canonical schema JSON,
schema name, schema fingerprint, and mode. Prompt and request reference
participate exactly as supplied before canonical string normalization.
Schema absence is not a V1 state: name and canonical JSON are required nonempty
strings, canonical JSON must decode to an exact object, and its supplied
fingerprint must equal the canonical schema SHA-256 before request hashing.

## 7. Byte canonicalization and SHA-256

Canonicalization is byte-for-byte identical to frozen Revision 3B:

1. normalize every string value and mapping key to Unicode NFC exactly once for
   fingerprint semantics; retain the raw source objects unchanged;
2. encode enums as their values;
3. encode tuples as JSON arrays in original order;
4. require exact built-in string mapping keys;
5. reject unsupported values and nonfinite numbers;
6. encode an aware datetime in UTC with exactly six fractional digits and `Z`;
7. encode temperature, top-p, and timeout as
   `{"type":"int|float","value":...}` so numeric types cannot collide;
8. serialize with `json.dumps(..., ensure_ascii=False, sort_keys=True,
   separators=(",", ":"), allow_nan=False)`; and
9. SHA-256 hash the canonical UTF-8 bytes and return exactly 64 lowercase
   hexadecimal characters without an algorithm prefix.

The supplied `requested_at` participates; the authority does not read a clock
or create a timestamp. Canonically equivalent Unicode produces the same
fingerprint. Different exact numeric types for tagged fields produce different
fingerprints. Mapping order does not affect output; sequence order does.

Version ownership is the package/version name
`editor-request-fingerprint-authority-v1`. V1 deliberately reproduces the
frozen Revision 3B bytes and adds no domain prefix because adding one would
invalidate existing requests. A future algorithm requires a new authority
version and cannot silently change V1.

## 8. Exact public authority API

The authority is stateless, frozen, slotted, and has no fields or `__dict__`.
Its exact constructor is:

```python
def __init__(self) -> None: ...
```

Its exact public methods are:

```python
def fingerprint(
    self,
    *,
    provider: ProviderChoiceV1,
    prompt: str,
    request_reference: str,
    requested_at: datetime,
    options: EditorGenerationRuntimeOptionsV1,
    output_schema_name: str,
    output_schema_canonical_json: str,
    output_schema_fingerprint: str,
    cancellation: CancellationTokenV2,
) -> str: ...

def reconstruct(
    self,
    fingerprint: str,
    *,
    provider: ProviderChoiceV1,
    prompt: str,
    request_reference: str,
    requested_at: datetime,
    options: EditorGenerationRuntimeOptionsV1,
    output_schema_name: str,
    output_schema_canonical_json: str,
    output_schema_fingerprint: str,
    cancellation: CancellationTokenV2,
) -> str: ...
```

`fingerprint` validates/reconstructs inputs, constructs canonical bytes once,
hashes once, and returns the result. `reconstruct` requires an exact built-in
lowercase 64-character hexadecimal string, independently calls the same
authority-internal calculation once, compares with `hmac.compare_digest`, and returns the
recalculated built-in digest only on equality. It does not accept prefixed or uppercase
forms. Neither method mutates or retains an input.

The class repr is exactly `EditorRequestFingerprintAuthorityV1()` and contains
no input or address. Equality is exact-type stateless equality and invokes no
foreign equality hook. Shallow and deep copy return identity without traversing
inputs. Pickle is rejected with
`EditorRequestFingerprintAuthorityV1 does not support pickle` before traversal.

## 9. Collision and reconstruction policy

The authority is stateless and has no historical collision registry. It MUST
NOT claim global SHA-256 collision detection. Within one reconstruction,
different canonical bytes accompanied by a supplied fingerprint from another
payload fail because the recalculated fingerprint differs. If an actual
SHA-256 collision produces equal digests, it is not representably detectable
without retaining forbidden global state; this limitation is explicit.

Repeated identical inputs produce identical canonical bytes and fingerprints.
Semantic fingerprint equality means both canonical payload bytes and digest are
equal; digest equality alone never establishes semantic equality when both
payloads are available.
Reconstruction never trusts string shape alone. Copied-invalid nested values,
schema mismatch, or changed semantic fields fail even when the supplied digest
is syntactically valid.

## 10. Error model and isolation

`EditorRequestFingerprintAuthorityError` subclasses `Exception`, has no extra
fields, and has exactly one public message:

```text
Editor request fingerprint authority is invalid.
```

Invalid input, canonical serialization failure, invalid fingerprint,
fingerprint mismatch, copied-invalid state, and reconstruction failure all map
to that error from no cause or context. Provider and execution failures do not
exist at this boundary.

Validation occurs in private outcome functions. Before raising the public
error, public frames delete authority-bearing arguments. Package-owned
traceback frames, closures, containers, and nested exception graphs retain no
prompt, schema, option, cancellation, timestamp, fingerprint, or foreign
object. Raw validation and serialization exceptions are discarded.

## 11. Dependency direction and future use

The dependency direction is exactly:

```text
LanguageModelProvider adapter
  -> package-private _EditorGenerationApplicationRequestBuilderV1
  -> EditorRequestFingerprintAuthorityV1
  -> EditorGenerationApplicationRequestV1
  -> EditorGenerationRequestAuthorityV1
  -> ProviderExecutionRequestV2
```

The new authority imports only public `ProviderChoiceV1`,
`CancellationTokenV2`, and `EditorGenerationRuntimeOptionsV1` contracts plus
standard-library canonical primitives. It does not import
`editor_generation_authority_v1.canonical`, private model helpers, the adapter,
workflow/runtime, provider implementations, or coordinator contracts.

The package-private `_EditorGenerationApplicationRequestBuilderV1` specified in
Execution Specification V2 is the Revision 3C application-request construction
owner. It supplies the nine authoritative values to `fingerprint()` exactly
once and immediately constructs/reconstructs the frozen application request
with the returned digest. It is not exported and owns no fingerprint algorithm.
No component, including the adapter, independently computes a fingerprint.

There is no circular dependency: the fingerprint package depends on public
value contracts; the future application-request authority depends on the
fingerprint package; the lower request authority consumes the finished value.

## 12. Passive behavior

Import, construction, repr, equality, copy, deepcopy, and rejected pickle
perform zero provider selection/execution, networking, credential/environment
access, client construction, runtime/workflow access, filesystem/database
access, clock access, randomness, retry, timeout enforcement, cancellation
polling, cleanup, persistence, logging, warning, stdout, stderr, thread, or
subprocess activity. Explicit method calls perform only validation,
canonicalization, and hashing.

There is no module registry, cache, singleton instance, mutable module state,
service locator, runtime discovery, observer, or cleanup method.

## 13. Adversarial implementation test plan

The focused offline test file is exactly:

```text
tests/test_editor_request_fingerprint_authority_v1.py
```

It covers:

1. exact files, ordered exports, symbol count, constructor and method signatures;
2. byte-for-byte parity with frozen Revision 3B for representative requests;
3. every included field changed independently changes the fingerprint where
   semantics differ;
4. explicit exclusion of runtime, execution, environment, and output state;
5. NFC composed/decomposed equivalence without source mutation;
6. UTC-equivalent datetimes and exact six-digit serialization;
7. integer/float tagged-field separation and nonfinite rejection;
8. canonical schema JSON/fingerprint agreement and mapping-order stability;
9. deterministic repeated fingerprint and successful reconstruction;
10. malformed, uppercase, prefixed, foreign, and mismatched fingerprint rejection;
11. copied-invalid options/cancellation and primitive subclass/coercion rejection;
12. collision limitation plus detectable cross-payload mismatch;
13. exact safe error/message/cause/context and recursive traceback isolation;
14. address-free repr, stateless equality, identity copy/deepcopy, pickle rejection;
15. passive fresh-process package/submodule imports and inert construction;
16. zero provider, adapter, workflow, runtime, execution, retry, persistence,
    filesystem, environment, cleanup, thread, and subprocess calls;
17. forbidden-import and dependency-direction scan; and
18. cross-process fingerprint equality for identical explicit inputs;
19. attempt-one/attempt-two parity proving distinct application references yield
    distinct fingerprints while the operation-scoped reference-factory fake
    proves linkage to the same operation authority;
20. frozen integrity, focused/full suite, Ruff, Black, compileall, pip check,
    and diff check.

Revision 3C's focused adapter tests additionally inject a deterministic fake of
this exact public authority and prove one fingerprint call per adapter call,
exact nine-field argument identity/value/order, no caller fingerprint input,
successful frozen request reconstruction, rejection of a forged authority
digest, coordinated field/digest substitution failure, and zero private helper
imports.

No live provider, credential, network, localhost listener, or model is used.

## 14. Implementation gates and sequence

Revision 3B.1 fingerprint-authority implementation becomes ready only if:

- parity vectors prove exact frozen Revision 3B bytes;
- the public API is the exact two-symbol API above;
- no private Revision 3B helper is imported; the additive authority implements
  the normative V1 algorithm in sections 6–7 and proves parity;
- reconstruction and error isolation pass adversarial tests; and
- production changes are limited to the additive package and focused test.

After it is independently verified and frozen, Revision 3C implements the exact
package-private application-request builder and adapter composition specified
by Execution Specification V2. This sequencing prevents the adapter from
becoming the fingerprint owner while requiring no additional public factory.

The required rollout sequence is closed:

```text
Revision 3B.1 additive fingerprint-authority implementation
  -> independent verification
  -> separately authorized commit/tag
  -> joint freeze of Fingerprint Authority V1 and Execution Specification V2
  -> Revision 3C package-private request builder and adapter implementation
```

Revision 3C MUST NOT begin before the verified 3B.1 tag and specification freeze.

## 15. Final ownership statement

The request reference remains caller-owned identity. The provider/model,
generation options, schema authority, timeout, cancellation, prompt, and
requested-at value remain owned by their input authorities. This authority owns
only their canonical fingerprint projection and verification. The application
request construction boundary owns assembly. The lower request authority owns
provider-neutral request construction. No ownership overlaps.
