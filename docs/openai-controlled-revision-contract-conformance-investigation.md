# Controlled Revision contract conformance investigation

## Executive summary

Part 5J made zero live requests and changed no production behavior. Static
differential validation identified one exact synthetic match for the repeated live
signature: a text variant whose body is valid under the provider-visible schema but
whose `component_reference` is inconsistent with its declared text type. The JSON
Schema accepts this structure; the DTO model validator rejects it.

Root conclusion: `GENERATED_SCHEMA_ALLOWS_DTO_INVALID_OUTPUT`.

Recommended next milestone: `CREATE TARGETED SCHEMA-DTO ALIGNMENT CORRECTION`.

## Prior evidence

Parts 5G and 5H recorded the same content-free E2E-02 topology: 11 errors, one
affected component, one top-level error, ten nested errors, nine secondary union
errors, and primary category `invalid_component_shape`. Part 5I reproduced it once
on each of `gpt-4.1-mini` and `gpt-4.1`, without retries or fallback.

## Frozen boundaries

The prompt, component-shape instructions, schema generator, DTO, validators,
projection, interpreter, authorization, reconstructor, domain validation, gateway,
runtime, model, retries, and fallbacks were not modified. `jsonschema` was added to
development/test extras solely for standards-compliant Draft 2020-12 differential
validation.

## Provider contract and DTO inventory

- Text: required `component_type`, `component_reference`, `revised_text`; type is
  `opening`, `transition`, or `closing`; strings have length 1–100000, while the
  reference maximum is 100. Its DTO-only model validator requires reference/type
  correspondence.
- Story: required `component_type`, `component_reference`, `factual_summary`,
  `commentary_block_texts`, `ending`; type is `story`; reference has the story
  pattern; strings have length 1–100000; commentary has at most 100 items.
- CTA: required `component_type`, `component_reference`, `bridge_text`; type and
  reference are fixed to `call_to_action`; bridge length is 1–100000.
- Every variant and root object forbids additional properties. Fields are neither
  optional nor nullable and have no aliases or defaults.
- Root requires `revised_components`, with 1–50 items. DTO-only root validation
  requires unique references. Schema imposes no ordering rule.

## Generated JSON Schema

The exact submitted canonical schema uses `$defs` and a three-branch `anyOf`, in
text/story/CTA order, with no discriminator. Branches publish the DTO fields,
literals, required sets, additional-property policy, string constraints, reference
pattern, and array maximum.

- Schema SHA-256: `3a643d39384e92fddbabd9e176a1cbda6e7bc2539d1a3937c88fdc025f07d31c`
- DTO schema SHA-256: `3973409a1069fd0d9b965aeddb554604dda452bdb570631c443056288fdca6ee`
- Prompt contract SHA-256: `cb6f07d47ec80ee8dfa246e5151f4c5a625adac2372f05a7cbccf4cbc3ebbf1c`

Serialization is UTF-8 JSON with sorted keys and compact separators, hashed with
SHA-256.

## Schema-to-DTO and prompt alignment

All published variant fields, required sets, literals, additional-property rules,
string constraints, and array constraints align. Prompt field names exactly match
the DTO.

Two DTO rules are absent from the schema:

- text `component_reference` must correspond to `component_type`;
- component references must be unique across the root list.

The prompt communicates exact-reference copying and type preservation, but prose
cannot make those constraints schema-enforced. Authorization membership, complete
authorized-set equality, source type/order preservation, and source commentary
cardinality are post-schema semantic rules owned downstream.

## Union behavior

`component_type` is not configured as a Pydantic discriminator. Literal constraints
make one branch the natural candidate, but Pydantic still evaluates all branches
and expands their errors. Local cases prove that missing, foreign, wrong-body,
constraint, and model-validator failures all generate secondary branch noise.

The exact 11/1/10/9 topology is produced by a structurally complete text branch
that passes its field rules and then fails `reference_matches_type`. Nine errors
come from nonmatching story/CTA attempts, one nested error is the text model
validator, and the root list contributes the top-level minimum-item consequence.

## Synthetic failure reconstruction (J01–J15)

| Case | Errors | Nested | Union | Primary | Exact live match |
|---|---:|---:|---:|---|---|
| Missing story field | 11 | 10 | 9 | missing required field | No |
| Wrong CTA body field | 10 | 9 | 7 | missing required field | No |
| Text type/story body | 12 | 11 | 7 | missing required field | No |
| Story type/text body | 11 | 10 | 5 | missing required field | No |
| CTA type/text body | 11 | 10 | 7 | missing required field | No |
| Valid story plus foreign field | 13 | 12 | 11 | extra field | No |
| Empty story ending | 13 | 12 | 11 | constraint violation | No |
| Empty revised text | 12 | 11 | 10 | constraint violation | No |
| Empty commentary list | DTO valid | — | — | — | No |
| Empty commentary item | DTO valid | — | — | — | No |
| Null required string | 13 | 12 | 11 | invalid nested type | No |
| Missing component type | 13 | 12 | 11 | missing required field | No |
| Unknown component type | 13 | 12 | 11 | wrong component type | No |
| Text reference/type validator | 11 | 10 | 9 | invalid component shape | **Yes** |
| Duplicate reference | 1 | 0 | 0 | duplicate reference | No |

Every failing single-component case affected one component. The duplicate case is
root-only and independently detected.

## Differential validation (D01–D20)

- D01–D03: `SCHEMA_PASS_DTO_PASS`
- D04–D09: `SCHEMA_FAIL_DTO_FAIL`
- D10–D11: `SCHEMA_PASS_DTO_PASS` (empty commentary arrays/items are allowed)
- D12–D15: `SCHEMA_FAIL_DTO_FAIL`
- D16 duplicate references: `SCHEMA_PASS_DTO_FAIL` via root DTO validator
- D17 text reference/type mismatch: `SCHEMA_PASS_DTO_FAIL` via component validator
- D18 wrong order: `SCHEMA_PASS_DTO_PASS`, post-schema semantic contract
- D19 missing authorized component: `SCHEMA_PASS_DTO_PASS`, post-schema semantic contract
- D20 unauthorized component: `SCHEMA_PASS_DTO_PASS`, post-schema semantic contract

Totals: 8 schema/DTO passes, 10 schema/DTO failures, 2 schema-pass/DTO-fail cases,
and 0 schema-fail/DTO-pass cases.

## Exact-signature result

One required synthetic candidate exactly matches all eight comparison dimensions:
the DTO-only text reference/type validator case. The safe signature is unique within
the required matrix. It identifies the violated structural rule without revealing
the actual reference, type value, or provider content.

## Interpreter and reconstructor expectations

The interpreter decodes JSON and delegates directly to the same provider DTO; it
does not expect an alternative representation. The reconstructor dispatches on the
validated DTO classes, checks exact authorized-reference set membership, resolves
source positions, and requires story commentary cardinality to match the source.
These are correctly separated post-schema rules. No interpreter or reconstructor
contract mismatch was found.

## Key conformance answers

1. Schema and DTO fields align.
2. Both forbid foreign fields identically.
3. Published lengths and list cardinality align.
4. Custom validator rules are only partially represented.
5. Yes: reference/type mismatch and duplicates can be schema-valid but DTO-invalid.
6. No schema-fail/DTO-pass case was found.
7. No explicit discriminator exists; nonmatching branches are still evaluated.
8. Prompt field names match the schema.
9. Prompt describes source type preservation that schema alone cannot enforce.
10. Missing/foreign fields can create similar noise, but not the exact full signature.
11. The current signature is sufficient within the required candidate matrix.
12. No additional live structural fingerprint is required for this discrepancy.

## Privacy assessment

The artifact contains fingerprints, repository-owned variant/field names,
constraint categories, ownership classifications, and aggregate signatures only.
It contains no provider or source prose, prompt body, output, raw validation input,
reference values, request IDs, credentials, or exceptions.

## Findings

- **P5J-CONTRACT / high:** two cross-field rules are DTO-only. The observed exact
  match is the text reference/type rule. Follow-up: targeted schema/DTO alignment;
  architecture impact: none.
- **P5J-SCHEMA / high:** the text branch permits any nonempty reference up to 100
  characters. Impact: strict schema can admit a DTO-invalid component.
- **P5J-VALIDATOR / informational:** uniqueness is also DTO-only but does not match
  the live signature.
- **P5J-PROMPT / informational:** names and variant mappings are aligned; prose
  already communicates type/reference consistency.
- **P5J-UNION / informational:** union expansion accurately accounts for nine
  secondary errors.
- **P5J-DIAGNOSTIC / informational:** Part 5G reduction is accurate and sufficient
  for this matrix.
- **P5J-ARCHITECTURE / informational:** no ownership or runtime defect was found.

## Root conclusion and recommendation

Root conclusion: `GENERATED_SCHEMA_ALLOWS_DTO_INVALID_OUTPUT`.

Recommendation: `CREATE TARGETED SCHEMA-DTO ALIGNMENT CORRECTION`.

No production change is authorized by this investigation.
