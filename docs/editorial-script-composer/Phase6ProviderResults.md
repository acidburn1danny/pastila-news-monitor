# Phase 6.3 — Provider Execution Result Contracts

Status: **Implemented — awaiting independent verification**

## Purpose and authority

Phase 6.3 represents completed provider execution results. Provider output first
becomes an independent immutable authority hierarchy:

`OpenAIExtractedExecutionResult → OpenAIExtractedResponse → OpenAIExtractedResponseMessage`

Submitted result contracts are deterministic projections of that hierarchy. They
cannot authorize their own generated text or finish reason. Validation rebuilds
the expected projection from the extracted authority in the validation context,
then compares every semantic field. Correctly resealing substituted output does
not make it authoritative.

The full authority chain is:

`Phase 6.1 execution planning → Phase 6.2 provider mapping → Phase 6.3 results`

Phase 6.2 remains frozen authority. Phase 6.3 reconstructs and validates both the
authoritative `DraftProviderRequestPlan` and the independently sealed extracted
result before accepting submitted result lineage.
It creates no competing request or execution authority.

Phase 6.3 does not execute providers. Execution belongs to later phases.

## Contracts and ownership

The generic layer exposes `ProviderExecutionResult` and
`ProviderExecutionResultValidationContext`. The result contains a typed
`OpenAIProviderExecutionResult`; it never stores `Any`, arbitrary dictionaries,
SDK objects, HTTP payloads, or runtime configuration.

The independent authority layer exposes `OpenAIExtractedExecutionResult`,
`OpenAIExtractedResponse`, and `OpenAIExtractedResponseMessage`. The submitted
concrete layer exposes `OpenAIProviderExecutionResult`,
`OpenAIProviderResponse`, and `OpenAIProviderResponseMessage`. One authoritative
OpenAI request owns one ordered response, and that response owns one generated
message. Strings use repository-standard NFC normalization. Generated text is
semantically preserved after that canonical domain normalization; NFC-equivalent
decomposed bytes may therefore converge, while whitespace and line endings are
otherwise neither trimmed nor repaired.

The provider identifier remains closed to `openai`. Finish reasons are closed to
`stop`, `length`, and `content_filter`; arbitrary provider strings are rejected.

## Canonical references and seals

Private shared derivations produce:

- `openai-extracted-execution-result:<openai-request-plan-identity>`
- `openai-extracted-response:<openai-request-identity>`
- `openai-extracted-response-message:<openai-request-identity>:<ordinal>`
- `provider-execution-result:<provider>:<provider-request-plan-identity>`
- `openai-provider-execution-result:<openai-request-plan-identity>`
- `openai-provider-response:<openai-request-identity>`
- `openai-provider-response-message:<openai-request-identity>:<ordinal>`

All semantic fields participate in deterministic identities. Fingerprints include
identity and all remaining semantic fields except the fingerprint itself. Ordered
response and message tuples use explicit indexed identity payloads. Serialization
uses repository-standard NFC-normalized canonical UTF-8 JSON and SHA-256.

## Builders, validation, and reconstruction

The preferred authoritative builders accept a Phase 6.2 request plan, one
independent `OpenAIExtractedExecutionResult`, and immutable validation context:

```python
build_openai_provider_execution_result(plan, extracted_authority, context)
build_provider_execution_result(plan, extracted_authority, context)
```

The compatibility-only four-argument form accepts generated-output and closed
finish-reason tuples only when identical authority already exists in the context.
It cannot create, replace, merge, reorder, or repair authority and is not the
preferred interface. It may be removed by a future compatibility-breaking phase.
Builders perform no transport, SDK parsing, repair, inference, caching, or input
mutation.

Validators enforce Phase 6.2 request-plan authority, execution and draft lineage,
request ownership, canonical references, seals, tuple order, duplicates, and
completeness. Submitted results are reconstructed before validation, and expected
structure is rebuilt from frozen authority. No submitted lineage is authoritative.

Response tuples retain authoritative request order; response ordinals must match
that order. Every response owns exactly one message at ordinal zero. Duplicate
references, identities, request ownership, and ordinals are detected before
lookup construction. There is no sorting, last-write-wins behavior, silent repair,
or placeholder generation.

## Canonical empty representation

An empty Phase 6.2 request plan is valid and reachable. Its unique Phase 6.3
representation is `responses == ()` in extracted, concrete, and generic results.
`None` and placeholders are not empty authority. Empty submitted results must
match empty extracted authority, and foreign empty lineage remains invalid even
when all response tuples are empty.

All extracted and submitted references are deterministic, authority-derived,
contextual domain references. They are not provider transport identifiers or
caller-controlled response IDs.

Ordinary reconstruction failures become bounded deterministic findings.
Process-control exceptions propagate unchanged. Diagnostic references use the
repository's bounded deterministic sanitization policy and never expose exception
messages or caller-controlled secrets.

All three public validator boundaries contain ordinary reconstruction failures,
including `AttributeError`, `KeyError`, `LookupError`, `RuntimeError`, `ValueError`,
`TypeError`, and Pydantic validation failures. `KeyboardInterrupt`, `SystemExit`,
and `GeneratorExit` remain process-control signals and propagate unchanged.

The approved independent extracted-result authority correction superseded the
original pre-correction inventory of five models and 17 symbols. Phase 6.3 now
intentionally freezes eight public models/context objects and 28 public symbols:
three extracted-authority models, three submitted OpenAI models, the generic
result and its validation context, three builders, three validators, seven
identity functions, and seven fingerprint functions.

## Execution boundary

This phase contains no SDK, HTTP, authentication, API key, environment access,
endpoint, model, sampling configuration, retry, timeout, streaming, tool calling,
response parsing, token usage, cost, latency, persistence, caching, logging,
telemetry, concurrency, scheduling, or generated-language behavior.

Later phases own provider execution and transport integration.

## Freeze-Coverage Boundaries

The canonical empty representation is `responses == ()` throughout the Phase
6.2 request plan, independent extracted authority, submitted OpenAI result, and
generic result. Equal empty tuples do not erase lineage: local and independently
valid foreign empty graphs retain distinct draft, execution-plan,
provider-request-plan, OpenAI-request-plan, extracted-result, and concrete-result
seals. Empty/nonempty validation is directional at each authority boundary.

Public validators reconstruct the outer artifact and its nested response/message
content as one fresh Pydantic snapshot. The execution-result, provider-plan,
mapping-context, submitted-result, and Phase 6.3 context arguments are directly
injectable reconstruction boundaries. Nested extracted responses/messages and
nested authorities inside a context have no independent public invocation point;
their authoritative reachable boundary is the containing extracted-result or
validation-context argument. Process-control propagation is frozen at those
nearest public boundaries, while ordinary reconstruction failures are contained.

Diagnostics contain no caller-owned mutable metadata. Tests preserve complete
issue tuples, serialization, `str`, and `repr` across deep caller mutation,
unrelated later validation, and separate Python processes. Cross-process coverage
includes malformed extracted/submitted artifacts, foreign authority, forged
seals, and empty foreign lineage.

The public Phase 6.3 API remains exactly 28 symbols: eight models/context types,
three builders, three validators, seven identity functions, and seven fingerprint
functions. Phase 6.3 performs no provider execution, transport, persistence, or
language-model invocation.

## Final Exhaustive Freeze Matrices

The committed freeze suite identifies every remaining scenario through named
pytest cases. It includes 17 empty-lineage dimensions, 17 independently valid
foreign-empty substitutions, every directional empty/nonempty authority case,
response and message cardinality, placeholder authority, and nested extra-field
reconstruction. Diagnostics are frozen as complete ordered structures and remain
immutable after caller-owned mappings and lists are mutated.

The subprocess inventory covers malformed, forged, foreign, empty, ownership,
placeholder, cardinality, and lineage families. Every one of the seven sealed
artifact levels is compared independently for complete dumps, seals, references,
tuple order, Unicode content, `str`, and `repr` stability.

Directly injectable process-control boundaries are the extracted result,
provider plan, mapping context, submitted OpenAI result, generic result, and
Phase 6.3 context arguments. Nested responses, messages, and authorities are
structurally unreachable as separate public arguments; their nearest authoritative
boundary is the containing result or context. The matrix freezes propagation at
those reachable boundaries.

Independently named regressions are retained because representative or aggregated
tests cannot prove that every ownership direction remains frozen. Production
behavior and the exact 28-symbol API are unchanged. Phase 6.3 remains implemented
and awaiting independent verification.

## Final Evidence Integrity

Collected names are not evidence by themselves. Every freeze scenario must use
an explicit construction path; unknown identifiers fail during construction, and
unrelated ownership, cardinality, placeholder, foreign, and subprocess cases may
not fall back to a shared malformed artifact.

Response and message cardinality cases construct their named tuple, ownership,
lineage, foreign, container, or authority condition directly. The foreign-empty
registry is separate from field-level empty-lineage mutation and inserts authority
components from independently valid foreign graphs. An empty graph has no response
or message child, so child coverage is called the nearest structurally reachable
foreign response or message substitution, never a foreign empty child.

Expected issue-code tuples are explicit freeze data. Caller-mutation, nested
extra-field, process-control, and subprocess matrices preserve complete ordered
diagnostics rather than issue existence alone. Artifact subprocess payloads expose
canonical serialization and canonical references separately for all seven sealed
levels. Production behavior and the exact 28-symbol API remain unchanged, and
Phase 6.3 remains awaiting independent verification.

## Final Complete Freeze Evidence

The final evidence harness is test-only and changes no production module. Its
explicit registries freeze these exact counts: 44 subprocess diagnostics, 18
caller-mutation families, eight nested-extra-field layers, 16 response cases,
20 message cases, 17 empty-lineage dimensions, 17 independent foreign-empty
substitutions, 54 process-control boundary/exception combinations, seven
cross-process artifact representations, and 12 meta-integrity safeguards.

The 44 subprocess scenarios are: malformed extracted result/response/message;
malformed OpenAI result/response/message; malformed generic result and context;
forged identity/fingerprint/seal at extracted, OpenAI, and generic levels;
foreign canonical references at those three levels; foreign-empty extracted,
OpenAI, and generic authority; extracted/OpenAI/generic empty-to-nonempty
mismatches; response and message omission/excess/duplication/reordering; four
extracted/OpenAI response/message placeholders; nested extra fields; and wrong
provider, request-plan, provider-plan, execution-plan, and draft lineage.

The 18 mutation families cover eight malformed reconstruction layers, forged
identity/fingerprint/seal, foreign canonical reference, foreign-empty authority,
empty/nonempty mismatch, response and message cardinality, placeholder authority,
and nested extra fields. The eight extra-field cases correspond exactly to the
three extracted models, three submitted OpenAI models, generic result, and
validation context. The response and message registries enumerate all cases in
the Phase 6.3 complete-freeze specification; every entry carries an explicit
ordered golden code tuple rather than learning expectations from the validator.

The process-control registry is the Cartesian product of the five extracted,
six OpenAI, and seven generic logical boundaries with `KeyboardInterrupt`,
`SystemExit`, and `GeneratorExit`. Nested response/message and context-member
boundaries have no independent public callable; each is therefore exercised at
its documented nearest owning public reconstruction argument. The original
exception instance is required to escape unchanged.

Each of the seven artifact subprocess records has ten distinct fields: complete
model dump, canonical serializer output, identity, fingerprint, canonical
reference, complete seal tuple, nested tuple order, NFC-normalized Unicode,
`str`, and `repr`. Scenario descriptors returned from subprocesses must name the
requested ID exactly. Registries reject unknown IDs and contain no default or
fallback entry. Empty graphs contain no response or message child, so the two
child-oriented cases are explicitly named nearest-reachable foreign response and
message substitutions.

The 12 meta-integrity safeguards freeze constructor presence, unknown-ID
rejection, response/message constructor isolation, 44-way subprocess specificity,
lineage/foreign-registry separation, 18-way mutation collection, eight-layer
extra-field collection, all 54 process-control combinations, non-null explicit
golden tuples, complete diagnostic assertions, and subprocess descriptor
identity. Phase 6.3 remains implemented and awaiting independent verification;
it is not marked verified or frozen here.
