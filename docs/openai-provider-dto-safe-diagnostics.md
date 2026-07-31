# OpenAI provider DTO safe diagnostics

## Part 5F baseline

Part 5F established that E2E-02 reached provider response extraction, JSON
decoding, and `OpenAIControlledRevisionProviderOutput.model_validate()`, where
validation failed. The historical provider payload was intentionally not retained,
and the available top-level evidence was insufficient to classify the nested
failure. The baseline classification was therefore `DIAGNOSTIC_INSUFFICIENT`.

## Diagnostic design

Part 5G adds a diagnostic-only reducer around Pydantic validation errors. It does
not change the provider DTO, generated schema, prompt, projection, interpreter
mapping, authorization, reconstruction, retry policy, or fallback behavior.

Raw locations are converted to stable shapes such as
`revised_components[*].component_type` and
`revised_components[*].commentary_block_texts`. Component indexes, union class
names, and unknown field names are removed. Raw Pydantic types are mapped into a
repository-owned taxonomy. The result exposes deterministic error and location
histograms, affected-component counts, top-level and nested counts, and a probable
primary category.

For untagged-union failures, the reducer prefers the branch whose discriminator
literal matched, then uses error count and a stable branch name as tie-breakers.
Errors from other attempted branches are counted as `union_branch_mismatch` rather
than independent provider defects. DTO-level duplicate-reference failures are
recognized separately at the model-validator location.

## Privacy boundary

Retained metadata is limited to normalized locations, canonical categories,
aggregate counts, and boolean diagnostic flags. The reducer never serializes raw
validation input, provider output, field values, prose, component references,
component indexes, prompts, exception messages, Pydantic context, request IDs, or
credentials. The local privacy matrix verifies this using synthetic markers.

## Local diagnostic matrix

G01-G25 pass. The matrix covers valid text/story/CTA objects, missing fields,
literal mismatches, mislabeled shapes, extra fields, nested primitive types,
cardinality and string constraints, reference patterns, duplicate references,
multi-component failures, union expansion, unknown error types, model-validator
locations, index removal, and prohibited-data absence.

## Controlled replay

Exactly one E2E-02 request was made under `SCOUT_RUN_LIVE_OPENAI_PART5G=1`, with
one runtime attempt, SDK retries disabled, and no provider or model fallback.
The response was received, extraction and JSON decoding completed, and provider
DTO validation was entered but did not pass.

Safe replay evidence:

- total validation errors: 11;
- unique categories: 3;
- affected components: 1;
- top-level errors: 1;
- nested errors: 10;
- union-branch errors: 9;
- model-validator-location errors: 0;
- probable primary category: `invalid_component_shape`;
- union expansion suspected: yes;
- duplicate-reference validator triggered: no;
- runtime attempts / SDK requests: 1 / 1;
- duration: 3409 ms;
- token usage, provider request ID, and returned model metadata: unavailable.

The canonical histogram was one `model_validator_failure`, one `too_short`, and
nine `union_branch_mismatch` errors. The normalized locations included only the
top-level collection and content-free component field shapes.

## Root-cause decision

The replay rules out duplicate references and demonstrates that most raw failures
were union expansion around one primary malformed component shape. Because the
payload was not retained and schema conformance was not independently established,
the evidence does not justify a schema-enforcement or schema/DTO-alignment claim.
The permitted classification is:

`PROVIDER_RETURNED_MALFORMED_COMPONENT`

The targeted next step is a provider-instruction correction that makes the
component type, reference, and matching component body shape explicit. Architecture
reassessment is not indicated.
