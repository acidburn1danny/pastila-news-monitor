# OpenAI provider DTO schema-failure investigation

Part 5F investigates the clean-restart E2E-02 failure without changing production
behavior. The provider runtime, client, schema, DTO, projection, prompt,
interpreter, reconstruction, domain, gateway, and acceptance system remain frozen.

## Failure trace

The synthetic E2E-02 story is placed in a `ControlledRevisionInvocation`. The
OpenAI projector exposes only the authorized story component and constructs an
`OpenAIResponsesPayload`. Its request arguments submit the canonical JSON Schema
to the Responses API in strict mode. `OpenAIProviderClient` returns the SDK
`Response` unchanged. The interpreter requires one completed output message and
one output-text part, parses that text as JSON, then calls
`OpenAIControlledRevisionProviderOutput.model_validate()`.

The clean restart failed during that Pydantic call. Reference authorization and
reconstruction occur afterward and were not entered. The original provider payload
was intentionally not retained and is unavailable for local replay.

## Schema and DTO

The top-level strict object requires only `revised_components`, rejects additional
properties, and constrains the array to 1–50 items. Items use an `anyOf` union:

- simple text components require type, reference, and revised text;
- story components require type, reference, factual summary, commentary-block
  text array, and ending;
- CTA components require type, reference, and bridge text.

Every nested object rejects additional properties. Strings have bounded non-empty
constraints where appropriate. Component types use literals/enums, story references
use a positive-ID pattern, and no DTO field is nullable. The story commentary array
has a maximum of 100 items and no schema minimum.

All DTO fields are provider-authored. Invocation identity, protected state,
ordering, lineage, fingerprints, and derived episode text are deliberately absent.
There are no aliases or provider metadata fields.

The projection, generated schema, and declared DTO fields/types are aligned. One
intentional expressiveness gap remains: the DTO's model validator rejects duplicate
component references, while JSON Schema cannot express uniqueness by one nested
field. Alignment is therefore `DTO_STRICTER_THAN_SCHEMA` for cross-item reference
uniqueness, and otherwise aligned.

## Prompt, SDK, and interpreter

Prompt alignment is `PROMPT_EXPLICIT`: the projector requires strict structured
output, exactly one revision for each supplied reference, no extra components, and
no prose outside the structured result. Required field structure and nullability
are communicated by the strict JSON Schema rather than duplicated in prose.

No SDK transformation is observed. The adapter passes field names and schema to the
SDK and later receives the SDK response object unchanged. The interpreter extracts
the single text part and parses JSON before DTO construction.

## Local matrix

D01–D15 cover a perfect payload; missing, extra, null, enum, and type errors; empty
and duplicate arrays; unknown references; extra metadata; alternative ordering;
minimal and maximum valid payloads; and malformed nested content. Additional tests
verify strict required/additional-property policy and the cross-item uniqueness gap.
No provider call is involved.

## Replay policy

If static evidence does not identify the historical payload's exact violation, one
E2E-02 replay may run only under `SCOUT_RUN_LIVE_OPENAI_PART5F=1`. A delegating
harness recorder retains only the interpreter's existing sanitized metadata:
validation stage, error count, first top-level field, Pydantic error type, and input
presence classification. It never retains the payload, values, prose, exception,
request ID, or credentials.

## Replay result — 28 July 2026

The single E2E-02 replay reproduced the failure. One provider response was received
after one runtime/SDK attempt. The strict schema was generated, JSON extraction and
decoding completed, and DTO validation was entered. DTO validation did not
complete; authorization, reconstruction, domain validation, and gateway creation
were not entered. No retry or fallback occurred.

Existing sanitized metadata reported stage `provider_dto`, 31 validation errors,
first top-level field `revised_components`, and first Pydantic error type
`value_error`. Duration was 5,107 ms. Usage and provider identifiers were
unavailable after failed interpretation.

This evidence identifies the failure layer precisely but cannot identify the
offending nested field or distinguish among the locally reproduced DTO violations.
The raw provider payload is not retained and must not be reconstructed. Root-cause
classification is therefore `DIAGNOSTIC_INSUFFICIENT`, not prompt, schema, DTO,
model, SDK, or interpreter defect. The next step is an additional DTO diagnostic
that safely reports error-type histograms and normalized location-shape categories
without retaining values or prose.
