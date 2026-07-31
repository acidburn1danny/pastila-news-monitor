# Reference Contract Remediation Design

## Executive Summary

The preferred architecture is **C2 — Invocation-specific exact-reference
schema**. The provider adapter should project the already-authorized target set
into its strict output schema so that provider-visible reference constants,
component branches, and cardinality equal the invocation contract. Existing
canonical identifiers, DTO validation, reference registry, exact authorization,
deterministic reconstruction, gateway, and runtime remain authoritative and
fail closed.

This is a design decision only. No production component, benchmark artifact, or
history entry is modified, and no provider or benchmark execution occurs.

## Problem Statement

Production requires provider output to return the invocation-authorized
structural references exactly. Its generic provider schema validates reference
syntax and component shape, but not the current invocation's exact values.
Part 7C.1 returned 24 responses and no exact authorized reference set:

- 24 missing `story:101`;
- 14 scenarios with unknown references;
- 17 with known-but-unauthorized references;
- 2 with duplicate references;
- 0 malformed references;
- 0 authorization, reconstruction, or pipeline successes.

Runtime correctly rejected all output. The architectural question is therefore
how to align the provider-visible structural language with the exact authorized
language before unchanged runtime authorization executes.

## Evidence Summary

- **Part 7C:** 24 single attempts, no retries/fallbacks, no pipeline success.
- **Part 7D:** the prompt explicitly requires exact copying; the static schema
  accepts syntax-valid invocation-invalid values; exact authorization is
  deterministic and correct.
- **Part 7E:** early diagnostics safely capture ordered references, usage,
  latency, cost, and terminal stage without production changes.
- **Part 7C.1:** 24/24 responses were safely rejected; reference precision and
  recall were both 0; `opening` was the most common unauthorized and first
  invalid reference; `transition:1:1` was the most common unknown reference.
- **Production contracts:** authorization already owns the exact set and the
  OpenAI projector already owns provider-specific schema projection.

These observations prove systematic boundary misalignment. They do not prove
that authorization, registry, mapping, or reconstruction should be relaxed.

## Architectural Constraints

Every viable direction must preserve one provider request, one authorization
pass, one deterministic reconstruction, fail-closed behavior, deterministic
runtime, offline validation, immutable corpus, provider-independent domain
contracts, and no benchmark-specific production path.

Authorization, reference identity, reference registry, mapping, reconstruction,
EpisodeDraft validation, acceptance, runtime, retries, and fallbacks remain
authoritative. Any design that infers privileges from approximate provider
output is inadmissible.

## Candidate Discovery

The discovery pass considered ten ideas across prompt, schema, representation,
runtime ownership, and interaction:

1. prompt-only exact-reference reinforcement;
2. invocation-specific reference enums;
3. invocation-specific reference-keyed objects;
4. strict tool arguments constrained to authorized references;
5. opaque invocation handles;
6. reference-free ordered patch slots;
7. a static enum of all source references;
8. tolerant alias/normalization/fuzzy mapping;
9. runtime reference injection based on provider order;
10. a second repair request.

Ideas 2–4 are one architectural family: each makes the invocation-authorized
set the constrained provider language. Ideas 6 and 9 are one family: both move
identity ownership to ordered deterministic slots. These equivalence merges
leave seven architectural families.

Static registry-wide enumeration is dominated by exact invocation enumeration:
it prevents unknown values but still permits known unauthorized values. Tolerant
mapping violates exact authorization. Multi-request repair violates the
single-request constraint. All eliminated ideas remain recorded in the JSON ADR.

## Candidate Families

### C1 — Prompt-only reinforcement

**Architecture.** Keep the generic schema and exact runtime contract; change
only provider instruction and reference presentation.

**Strengths.** One small boundary changes. Runtime, DTO, schema, authorization,
and reconstruction remain compatible. It is operationally simple and portable.

**Weaknesses.** The frozen prompt already says to copy every reference exactly,
return each once, and return no unauthorized reference. Despite that, Part
7C.1 produced zero exact references. Natural-language adherence remains the
only invocation-specific enforcement.

**Consequences.** Fail-closed authorization remains safe, but the probability
of another zero-success benchmark is materially supported by existing data.

### C2 — Invocation-specific exact-reference schema

**Architecture.** At provider request projection, derive strict schema branches,
reference constants, and item cardinality from the invocation's already
authorized target set. Keep canonical references provider-visible and retain
unchanged DTO, registry, exact authorization, and reconstruction.

**Strengths.** It closes the exact gap demonstrated by Part 7D and Part 7C.1 at
the earliest enforceable boundary. Schema-valid unknown or unauthorized
references become unrepresentable. Canonical identity remains singular and
authorization remains defense in depth.

**Weaknesses.** Schema projection becomes invocation-specific. Projection
validation, DTO parity, capability mapping, and fingerprint/version semantics
require explicit migration and tests.

**Consequences.** The request remains single-attempt. Invalid projections can be
rejected offline before spending a provider request. Provider adapters may use
their native constrained-output mechanism without changing neutral domain
ownership.

### C3 — Opaque authorized handles

**Architecture.** Give each authorized target a short invocation-owned handle;
the provider returns handles, and an adapter maps them deterministically to
canonical references before authorization.

**Strengths.** Enum-constrained handles avoid semantic identifier invention and
can be provider-portable. Canonical references are never generated freely.

**Weaknesses.** This creates a second identity system, changes DTO/schema and
diagnostics, and adds handle scope, uniqueness, lineage, and mapping obligations.
Mapping drift introduces a new privilege-confusion surface.

**Consequences.** It requires the same invocation-specific constrained-value
capability as C2 but carries additional identity and migration cost. C2 therefore
strictly dominates it for the observed problem.

### C4 — Reference-free ordered patch slots

**Architecture.** The provider returns an ordered sequence of patch bodies;
runtime binds slots to the ordered authorized targets after strict count, order,
and type validation.

**Strengths.** Provider-authored reference strings disappear. The design is
portable and can use a compact schema.

**Weaknesses.** Identity becomes positional. Missing, extra, or reordered slots
can bind valid text to the wrong target unless every invariant is fail-closed.
Provider DTO and reconstruction ownership change materially, and output becomes
less self-describing.

**Consequences.** It trades spelling/reference confusion for ordering confusion
and requires new slot-alignment diagnostics and a contract-version migration.

## Comparative Matrix

Scores use a uniform 1–5 scale: 1 is material weakness, 3 is a bounded material
trade-off, and 5 strongly preserves or improves the criterion with low residual
risk. All 19 mandatory criteria have equal weight. Evidence notes and raw scores
are preserved in the structured artifact.

| Criterion | C1 Prompt | C2 Exact schema | C3 Handles | C4 Slots |
|---|---:|---:|---:|---:|
| Determinism | 5 | 5 | 5 | 5 |
| Provider compliance probability | 1 | 5 | 5 | 5 |
| Authorization compatibility | 5 | 5 | 5 | 4 |
| Reference integrity | 2 | 5 | 4 | 3 |
| Reference ownership | 2 | 5 | 4 | 5 |
| Operational simplicity | 5 | 4 | 3 | 4 |
| Runtime complexity | 5 | 4 | 3 | 3 |
| Prompt complexity | 2 | 5 | 4 | 5 |
| Schema complexity | 5 | 3 | 3 | 4 |
| Migration complexity | 5 | 4 | 2 | 2 |
| Testing complexity | 4 | 4 | 3 | 3 |
| Regression risk | 4 | 4 | 2 | 2 |
| Operational safety | 3 | 5 | 4 | 3 |
| Failure isolation | 3 | 5 | 4 | 3 |
| Maintainability | 3 | 4 | 3 | 3 |
| Extensibility | 3 | 4 | 3 | 4 |
| Provider portability | 5 | 4 | 3 | 4 |
| Offline validation | 3 | 5 | 5 | 5 |
| Future benchmark compatibility | 2 | 5 | 4 | 4 |
| **Total / 95** | **67** | **85** | **69** | **71** |

## Trade-off Analysis

### C1

The benefit is minimal migration. The cost is continued dependence on behavior
that failed uniformly. Operational safety remains fail closed, but productive
availability remains uncertain. Long-term maintenance becomes repeated prompt
and model revalidation.

### C2

The benefit is early equivalence between schema-valid and authorization-valid
references while retaining one canonical identity. The cost is dynamic schema
projection and version/fingerprint migration. Projection defects become visible
offline; final authorization still contains them. Long term, a neutral
authorized-set contract can be mapped by each provider adapter.

### C3

The benefit is a compact provider vocabulary. The cost is permanent dual
identity, a mapper, broader DTO migration, and mapping-lineage security tests.
It reduces semantic invention but creates handle confusion without outperforming
C2's constrained canonical values.

### C4

The benefit is eliminating provider identity generation. The cost is making
order/cardinality security-critical and changing DTO/reconstruction ownership.
It is extensible across providers but less self-describing and introduces a new
class of wrong-slot failures.

## Failure Analysis

### C1

Expected failures are repeated schema-valid alternate references and
prompt/model sensitivity. They are visible only after a paid response, contained
by unchanged authorization, and recoverable only through another prompt version
and benchmark. Reproducibility requires prompt fingerprints.

### C2

Expected failures are invalid dynamic schema, provider rejection of constraints,
or DTO/schema branch drift. Most are detectable during offline projection.
Preflight abort contains them before transport; unchanged authorization remains
the final guard. Rollback changes the projector/version without data migration.

### C3

Expected failures are unknown/duplicate handles and handle-to-canonical mapping
drift. Schema catches many values; mapping validation catches the remainder.
Containment is fail closed, but rollback spans schema, DTO, mapper, and
diagnostics. Benchmarks require handle-specific metrics.

### C4

Expected failures are missing, extra, reordered, or wrong-shaped slots. They are
detectable after response and must be rejected before binding. Recovery spans
DTO and reconstruction contracts. Reference benchmarks become slot-alignment
benchmarks, reducing direct historical comparability.

## Security Analysis

C1 preserves exact authorization but leaves provider-boundary ambiguity and
reference-confusion exposure unchanged. C2 constrains output to exact authorized
constants and retains final authorization, providing defense in depth without a
new privilege path. C3 introduces capability-like handles whose scoping and
mapping become security-critical. C4 removes spoofable identifiers but creates
position-confusion risk. No viable candidate permits fuzzy or inferred
authorization.

## Migration Analysis

| Candidate | Components | Compatibility | Deploy | Rollback | Effort |
|---|---|---|---|---|---|
| C1 | Prompt projection | Runtime-compatible; prompt fingerprint changes | Low | Low | Low |
| C2 | Schema projector and schema identity diagnostics | DTO/runtime-compatible; projected fingerprint strategy required | Moderate | Low | Moderate |
| C3 | Projector, schema, DTO, mapper, diagnostics | Contract-version transition | High | Moderate | High |
| C4 | Schema, DTO, mapping, reconstruction boundary, diagnostics | New output contract version | High | Moderate | High |

C2 implementation testing must cover every target type, multi-target cardinality,
DTO parity, invalid projection preflight, provider capability boundaries,
unchanged authorization/reconstruction, privacy, and a separately authorized
post-implementation baseline.

## Candidate Ranking

1. **C2 Dynamic exact schema — 85/95**
2. **C4 Ordered patch slots — 71/95**
3. **C1 Prompt-only — 67/95**
4. **C3 Opaque handles — 69/95, dominated by C2**

C3's numeric score exceeds C1 but it is ranked last because dominance is a
hard architectural result: C2 performs at least as well on the relevant
constrained-value guarantees while avoiding the additional identity system.
The ranking is therefore score-ordered only among non-dominated candidates.

## Recommended Architecture

Select **C2_DYNAMIC_EXACT_SCHEMA**: invocation-specific exact-reference provider
schema projection.

Why this candidate:

- It directly addresses the proven static-schema/exact-authorization gap.
- It makes all 24 observed missing/unknown/unauthorized patterns structurally
  unrepresentable without relaxing any runtime guard.
- It preserves canonical reference ownership rather than adding handles or
  positional identity.
- It permits offline validation before a paid request.
- It retains one request, one authorization pass, one reconstruction, and
  provider-neutral domain contracts.

Guarantees improved: provider-boundary reference integrity, early failure
detection, failure isolation, and benchmark diagnosability.

Guarantees unchanged: exact authorization, fail-closed reconstruction,
deterministic runtime, gateway semantics, source provenance, retry/fallback
policy, and benchmark corpus.

## Rejected Alternatives

- **C1:** the prompt already expresses the required rule and measured compliance
  was 0/24; it does not close the structural gap.
- **C3:** dominated by C2 because it needs the same constrained-value capability
  while adding dual identity and mapping risk.
- **C4:** viable but changes identity ownership and creates positional confusion
  that the evidence does not require accepting.
- **Static registry enum:** prevents unknown, not unauthorized, references.
- **Tolerant mapping:** weakens exact authorization and increases spoofing risk.
- **Repair request:** violates the single-request guarantee.

## Future Work

The next implementation milestone must first freeze the projected-schema
contract, base/projected fingerprint semantics, DTO parity rules, exact
reference/cardinality invariants, and provider-capability abstraction. It must
leave final authorization and reconstruction unchanged and prove all invariants
offline before any separately authorized provider validation.

No implementation or benchmark execution belongs to Part 7F.

## Architecture Impact

**MODERATE** expected future implementation effort. The change is localized to
provider schema projection and schema identity diagnostics, but it evolves a
previously frozen production contract and therefore requires comprehensive
compatibility and regression proof.

## Root Conclusion

`SCHEMA_REMEDIATION_RECOMMENDED`

## Final Recommendation

`IMPLEMENT_SELECTED_REFERENCE_CONTRACT`
