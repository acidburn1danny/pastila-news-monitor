# Controlled Revision component-shape instruction correction

## Prior evidence

Part 5G classified the E2E-02 provider DTO failure as
`PROVIDER_RETURNED_MALFORMED_COMPONENT`. One component produced 11 validation
errors: one primary invalid-component-shape failure, one collection constraint
error, and nine secondary union-branch errors. Duplicate-reference validation did
not trigger.

## Targeted correction

The OpenAI Controlled Revision projector owns one concise provider-facing
component-shape instruction block. It applies to every OpenAI controlled-revision
request and is not scenario-specific. It now states that references must be copied
exactly, component types must be preserved, every authorized reference must appear
exactly once, unauthorized references are prohibited, and every object must use one
complete non-hybrid component shape.

The documented variants use the production DTO field names:

- text components use `component_type`, `component_reference`, and `revised_text`;
- story components use `component_type`, `component_reference`,
  `factual_summary`, `commentary_block_texts`, and `ending`;
- call-to-action components use `component_type`, `component_reference`, and
  `bridge_text`.

A final semantic self-check reinforces reference cardinality, authorization, type
identity, required fields, and exclusion of foreign fields. Strict JSON Schema
serialization remains required.

## Frozen boundaries

The production JSON Schema, provider DTO and validators, projection data mapping,
interpreter, reference authorization, reconstructor, EpisodeDraft validation,
gateway, provider-neutral runtime, retries, fallbacks, and editorial semantics were
not changed. The frozen schema SHA-256 remains
`3a643d39384e92fddbabd9e176a1cbda6e7bc2539d1a3937c88fdc025f07d31c`.

## Local verification

H01-H15 pass. They verify exact reference copying, one-to-one cardinality,
unauthorized-reference prohibition, type preservation, all three concrete shapes,
hybrid prohibition, required/foreign fields, the completion self-check, frozen
schema, frozen DTO behavior, unchanged editorial instructions, and generic scope.

M01-M12 pass. Valid text, story, and CTA variants remain accepted. Mislabeled,
incomplete, hybrid, extra-field, invalid-reference, and duplicate-reference objects
remain rejected. Validation was not weakened.

The dry run performed zero provider and SDK requests. Before replay, 163 focused
tests and the complete 874-test suite passed, as did Ruff, Black, compileall, and
dependency validation.

## Controlled replay

Exactly one E2E-02 request was made under `SCOUT_RUN_LIVE_OPENAI_PART5H=1`, with
one runtime attempt, SDK retries disabled, and no provider or model fallback. The
provider response was received and JSON decoding completed. DTO validation was
entered but failed before reference authorization, reconstruction, EpisodeDraft
validation, or gateway validation.

The sanitized failure signature was unchanged from Part 5G:

- total validation errors: 11;
- unique categories: 3;
- affected components: 1;
- top-level errors: 1;
- nested errors: 10;
- secondary union-branch errors: 9;
- probable primary category: `invalid_component_shape`;
- union expansion suspected: yes;
- duplicate-reference validator triggered: no;
- request duration: 6631 ms;
- token usage, request ID, and returned model metadata: unavailable.

No provider content, source prose, revised prose, prompt body, request or response,
validation input, exception, reference value, request ID, or credential was printed
or retained.

## Decision

The same malformed-component category recurred despite explicit component-shape
instructions. Per the Part 5H decision rule, the classification is
`MODEL_STRUCTURED_OUTPUT_RELIABILITY_LIMITATION`.

The final recommendation is `CREATE MODEL STRUCTURED-OUTPUT RELIABILITY ASSESSMENT`.
The prompt should not be expanded further without that assessment.
