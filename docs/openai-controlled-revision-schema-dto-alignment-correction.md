# Controlled Revision schema–DTO alignment correction

## Executive summary

Part 5K aligns the provider-visible schema with the existing DTO
`reference_matches_type` rule. The historical synthetic mismatch is now rejected by
both schema and DTO. No live request has been made; replay remains subject to
separate approval.

Root conclusion: `SCHEMA_DTO_ALIGNMENT_CORRECTED`.

## Proven Part 5J defect

The former text branch allowed any nonempty reference up to 100 characters. A
text-shaped object could therefore pass the submitted schema and later fail the
DTO when its reference category disagreed with `component_type`. This uniquely
reproduced the repeated 11-error signature.

## Correction scope and authoritative rules

The existing opening and closing literals and conservative transition numeric-pair
pattern are now repository-owned constants used by both the DTO validator and
schema customization. Story and CTA constraints remain their existing pattern and
literal. No reference is normalized or repaired.

## Schema generation change

The root `anyOf` remains text/story/CTA. Only the text `$defs` entry is strengthened:
it contains three complete object branches for opening, transition, and closing.
Each branch retains required fields, additional-properties rejection, string
constraints, and exactly one reference rule matching its type. The canonical
schema returned by `controlled_revision_schema_json()` is the same schema placed in
the Responses API strict structured-output request.

The implementation uses only `anyOf`, `const`, `pattern`, `required`, and
`additionalProperties`; no conditionals, recursion, or nonportable regex features
were introduced. The transition pattern uses anchors, literal separators, and
simple nonzero numeric groups.

## Frozen boundaries

The prompt, DTO fields and validation behavior, interpreter, authorization,
reconstructor, EpisodeDraft models, gateway, acceptance, provider-neutral runtime,
default model, credentials, timeout, retries, and fallbacks remain unchanged. The
DTO validator remains defense-in-depth for local callers and schema drift.

## Fingerprints

- Previous schema: `3a643d39384e92fddbabd9e176a1cbda6e7bc2539d1a3937c88fdc025f07d31c`
- Corrected schema: `70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556`

Both use UTF-8 canonical JSON, sorted keys, compact separators, and SHA-256.

## Differential validation

K01–K03 and K11 pass both schema and DTO. K04–K10 and K12 fail both. The
historical mismatch changed from `SCHEMA_PASS_DTO_FAIL` to
`SCHEMA_FAIL_DTO_FAIL`. Valid text, story, CTA, mixed, minimum-count, and
maximum-count payloads remain accepted.

Empty commentary arrays and empty commentary strings remain accepted because the
frozen DTO and schema define no minimum for those values. The maximum of 100
commentary items remains enforced. This preserves existing behavior rather than
silently introducing a new constraint.

## Remaining DTO-only and post-schema rules

Cross-item reference uniqueness remains DTO-only because it is a separate scope
and is not safely represented by ordinary JSON Schema `uniqueItems` when entire
objects differ. Authorization membership, exact authorized-set equality, source
ordering/type preservation, and source commentary cardinality remain downstream
semantic rules.

## Prompt and runtime stability

The prompt already communicates exact reference copying, type preservation, and
non-hybrid shapes; its fingerprint is unchanged. Interpreter, reconstructor,
runtime, retry, and fallback behavior are unchanged.

## Dry run and optional replay

The Part 5K harness loads E2E-02 and the corrected schema but remains disabled by
default. Its dry run reports zero provider and SDK requests. One E2E-02 replay on
the configured production model may run only after explicit approval.

## Privacy

The alignment artifact contains only fingerprints, repository-owned structural
categories, differential outcomes, and remaining rule ownership. It contains no
provider/source prose, output, prompt body, references, IDs, credentials, raw
inputs, or exceptions.

## Findings

- **P5K-SCHEMA / resolved:** the provider schema now enforces text type/reference
  correspondence. Impact: historical DTO-invalid shape is schema-invalid.
- **P5K-DTO / informational:** validator behavior is preserved as defense-in-depth.
- **P5K-REFERENCE / resolved:** opening, transition, and closing constraints share
  repository-owned rules.
- **P5K-UNION / informational:** root union architecture remains unchanged.
- **P5K-ARCHITECTURE / informational:** correction is localized to schema generation;
  no architecture reassessment is needed.

## Root conclusion and recommendation

Local root conclusion: `SCHEMA_DTO_ALIGNMENT_CORRECTED`.

Pending the separately authorized replay, the recommended next step is
`RESTART PART 5 WITH CORRECTED SCHEMA` only if DTO validation proceeds successfully.
