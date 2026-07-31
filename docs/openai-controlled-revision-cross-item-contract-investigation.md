# Controlled Revision cross-item contract expressibility investigation

## Executive summary

Part 5L made zero live and SDK requests and changed no production behavior. Local
Draft 2020-12 experiments show that generic `uniqueItems` cannot enforce
`component_reference` uniqueness when duplicate-reference objects have different
bodies. Exact enforcement is locally possible only with invocation-specific schema
generation or a contract redesign. Provider compatibility for the required new
keywords is not proven by the repository.

Root conclusion: `CURRENT_DTO_OWNERSHIP_IS_CORRECT`.

Recommendation: `KEEP_DUPLICATE_VALIDATION_IN_DTO`.

## Current ownership map

| Rule | Current owner | Schema | DTO | Reconstructor |
|---|---|---|---|---|
| Component-reference uniqueness | Provider DTO | No | Yes | Indirectly protected |
| Exactly-once occurrence | Reconstructor | No | Partial via uniqueness | Yes |
| Authorized-reference membership | Reconstructor | No | No | Yes |
| Complete authorized-reference set | Reconstructor | No | No | Yes |
| Source order preservation | Reconstructor | No | No | Yes |
| Component count equality | Reconstructor | No | No | Yes |
| One output per authorized input | Reconstructor | No | Partial | Yes |
| Absence of unauthorized outputs | Reconstructor | No | No | Yes |

All rules are provider-visible through instructions/input metadata, but only static
shape rules are visible to the current schema. The interpreter delegates DTO-valid
objects to the reconstructor; the gateway consumes the resulting authoritative
draft rather than independently enforcing patch-set rules.

## Rule classifications

- Component-reference uniqueness: `SCHEMA_PARTIALLY_EXPRESSIBLE`.
- Exactly-once occurrence: `SCHEMA_PARTIALLY_EXPRESSIBLE`.
- Authorized-reference membership: `SCHEMA_PARTIALLY_EXPRESSIBLE`.
- Complete authorized-reference set: `SCHEMA_PARTIALLY_EXPRESSIBLE`.
- Source order preservation: `SCHEMA_PARTIALLY_EXPRESSIBLE`.
- Component count equality: `SCHEMA_EXPRESSIBLE` through equal dynamic
  `minItems`/`maxItems`.
- One output per authorized input: `SCHEMA_PARTIALLY_EXPRESSIBLE`.
- Absence of unauthorized output: `SCHEMA_PARTIALLY_EXPRESSIBLE`.

All partial cases require invocation-specific identities, counts, or ordering.

## JSON Schema capability matrix

The local Draft 2020-12 validator supports every investigated keyword. Repository
evidence proves provider-path use only for the currently submitted subset,
including `items` and `const`. It does not prove provider compatibility for
`uniqueItems`, `contains`, `minContains`, `maxContains`, `prefixItems`,
`dependentSchemas`, `if/then/else`, `unevaluatedItems`, or
`unevaluatedProperties`.

- `uniqueItems`: compares complete array items, not one property across items.
- `contains` with `minContains`/`maxContains`: can enforce one dynamic identity
  exactly once, repeated for every authorized identity.
- `prefixItems`: can enforce exact identity, ordering, and cardinality dynamically.
- `enum`/`const`: can restrict membership but require authorized values to be
  generated per invocation.
- `dependentSchemas` and conditionals do not provide simple generic cross-item
  property uniqueness.
- `unevaluatedItems` and `unevaluatedProperties` close schema evaluation but do not
  independently establish identity uniqueness.

External provider documentation would be required to confirm support for
`contains`/`minContains`/`maxContains`, `prefixItems`, or `uniqueItems` in strict
Responses structured outputs. This investigation makes no compatibility claim.

## Candidate comparison

### Candidate A — current DTO ownership

The static schema accepts duplicates; the DTO rejects duplicate reference values.
It preserves a compact static schema and existing architecture.

### Candidate B — `uniqueItems`

Locally rejects identical duplicate objects but accepts two objects with the same
reference and different body content. It does not solve the observed failure.

### Candidate C — dynamic `contains`

Locally enforces allowed membership and exactly one occurrence per authorized
identity. It requires one generated constraint per input component and unproven
provider keyword support.

### Candidate D — dynamic `prefixItems`

Locally enforces exact order, identity, and cardinality. It couples the schema to
each invocation, has the highest measured schema growth, and uses unproven provider
keywords.

### Candidate E — object keyed by reference

Provides natural key uniqueness after JSON parsing and relatively compact dynamic
schemas, but changes ordering semantics and requires DTO, interpreter,
reconstructor, and provider-contract redesign. It is not a targeted correction.

## Dynamic schema size

Canonical synthetic schema sizes in bytes:

| Candidate | 1 | 10 | 25 | 50 |
|---|---:|---:|---:|---:|
| A — current | 250 | 250 | 250 | 250 |
| B — uniqueItems | 269 | 269 | 269 | 269 |
| C — contains | 436 | 1,853 | 4,238 | 8,213 |
| D — prefixItems | 304 | 1,882 | 4,522 | 8,922 |
| E — keyed object | 177 | 593 | 1,313 | 2,513 |

These figures measure simplified canonical schemas, not production request size.
They demonstrate relative growth and maintenance cost only.

## Architectural ownership

Duplicate-reference uniqueness is structural at the provider patch boundary and is
correctly enforced by the provider DTO. It also supports later semantic guarantees,
but does not require source access. Authorized membership, completeness, ordering,
and one-output-per-input are invocation-dependent semantic/authorization concerns
correctly owned by deterministic reconstruction.

Moving uniqueness into a dynamic schema would not eliminate the need for DTO
defense-in-depth. It would add projection-time contract generation and an
unverified provider dependency for limited benefit.

## Privacy and regression

The artifact contains only rule names, ownership categories, keyword capability
flags, aggregate candidate outcomes, and schema-size counts. It contains no source
or provider text, real or synthetic reference values, request IDs, credentials,
raw validation payloads, or exceptions.

No live execution path or SDK client exists in the investigation module.

## Findings

- **P5L-CONTRACT / high:** generic `uniqueItems` is insufficient for property-level
  uniqueness. Impact: it cannot prevent the observed duplicate-reference case.
- **P5L-SCHEMA / medium:** dynamic designs work locally but grow linearly and require
  invocation-specific contract generation.
- **P5L-PROVIDER / medium:** compatibility for the new cross-item keywords is not
  established by repository evidence.
- **P5L-DTO / informational:** current uniqueness validation is deterministic,
  content-free, and correctly placed as defense-in-depth.
- **P5L-ARCHITECTURE / informational:** source-aware exact-set and ordering rules
  remain correctly owned by reconstruction.

## Conclusion

`CURRENT_DTO_OWNERSHIP_IS_CORRECT`

## Recommendation

`KEEP_DUPLICATE_VALIDATION_IN_DTO`
