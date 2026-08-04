# Module 3.0 Revision 2 — Verified Runtime Consumer Discovery

Status: **verified-discovery candidate — no consumer migrated**

Frozen baseline: `module-2.9-complete` / `ed5ecb8035a504b6dc9b07f09576f7b8149629c9`

## Objective and architecture

Module 3 owns application rollout, compatibility, and transition management.
Module 2.9 remains immutable and continues to own provider contracts, execution,
request and result authority, registration and claim authority, and lifecycle.

Every arrow points from consumer to dependency:

```text
Application consumer
        |
        v
Module 3 application-owned migration boundary
        |
        v
ProviderExecutorV2 / ProviderExecutionRequestV2 / ProviderExecutionResultV2
        |
        v
Frozen Module 2.9
```

Revision 2 adds no runtime capability and performs no migration, composition,
provider execution, credential lookup, networking, CLI wiring, or GUI wiring.

## Consumer definition

A rollout consumer must be application-owned, directly depend on an
OpenAI-specific runtime execution boundary, and be a real migration candidate.
Static discovery classifies all relevant candidates before filtering them.

The controlled classifications are:

- `direct_runtime_consumer`
- `composition_root`
- `transitive_consumer`
- `provider_neutral_infrastructure`
- `frozen_module`
- `documentation_only`
- `test_only`

Frozen Module 2.9 packages, provider-neutral infrastructure, bridges, SDK
adapters, registration and claim authorities, tests, documentation, and
transitive protocol users are not rollout inventory entries.

## Discovery methodology

Discovery uses deterministic static AST inspection. It scans Python source in
lexicographic path order, never imports a candidate, and detects direct imports
of the official OpenAI SDK or the legacy OpenAI provider composition seam.
Known frozen Module 2.9 paths are excluded before parsing. Package-level files
belonging to one execution boundary are collapsed into one consumer package.

The package import is passive: the checked-in verified inventory is loaded
without running the repository scan. The explicit scanner exists to let tests
and independent verification reconcile current source against that inventory.

```text
Static discovery
      |
      v
Classified candidates
      |
      v
Verified descriptive inventory
      |
      v
Separate prescriptive migration plan
      |
      v
Future consumer-local migration
```

## Candidate classifications

| Package | Classification | Direct execution boundary | Migration candidate |
|---|---|---|---:|
| `pastila_scout.editor.generation.ai_provider_adapter.openai` | Direct runtime consumer | OpenAI controlled-revision adapter transport | Yes |
| `pastila_scout.ai.openai_provider` | Direct runtime consumer | Legacy structured-AI provider implementation | Yes |
| `pastila_scout.cli` | Composition root | Scout command provider composition | Yes |
| `pastila_scout.ai.verification` | Transitive consumer | No direct provider execution boundary | No |
| `pastila_scout.ai.editorial_scoring` | Transitive consumer | No direct provider execution boundary | No |
| `pastila_scout.editor.script_composer` | Frozen module | Frozen architecture, not an application migration seam | No |
| `pastila_scout.provider_composition_v2` | Provider-neutral infrastructure | Registry composition, not provider execution | No |

Test-only and documentation-only references are excluded during source-root
discovery rather than stored as package inventory entries.

## Verified descriptive inventory

The authoritative inventory contains exactly three current migration candidates:

1. `pastila_scout.editor.generation.ai_provider_adapter.openai`
2. `pastila_scout.ai.openai_provider`
3. `pastila_scout.cli`

Inventory records describe current package ownership, direct dependency,
classification, and execution boundary. They contain no migration order or
future revision assignment.

## Strict contract acceptance

Authoritative discovery, inventory, and migration-plan collections do not trust
retained objects merely because they have the expected Python type. Before
checking uniqueness or ordering, collection acceptance reconstructs every entry
field-for-field through its strict model contract. Blank, padded, substituted,
coerced, copied-invalid, deep-copied-invalid, and deserialized-invalid retained
state is therefore rejected before it can enter an authoritative collection.
No field is normalized or refreshed during revalidation.

The ordered public API is:

```text
RUNTIME_CONSUMER_DISCOVERY_V1
RUNTIME_CONSUMER_INVENTORY_V1
RUNTIME_MIGRATION_PLAN_V1
CompatibilityRiskV1
MigrationDifficultyV1
RuntimeConsumerClassificationV1
RuntimeConsumerDiscoveryRecordV1
RuntimeConsumerInventoryEntryV1
RuntimeMigrationPlanEntryV1
```

## Separate migration planning

Planning is prescriptive and may change after independent verification; it does
not redefine discovered reality. The initial plan is:

| Order | Consumer | Planned revision | Replacement boundary | Difficulty | Risk |
|---:|---|---|---|---|---|
| 1 | Producer OpenAI adapter | `3.0-r3-producer` | Replace only the Producer execution transport | High | High |
| 2 | Legacy Scout OpenAI provider | `3.0-r4-scout-runtime` | Preserve the structured-AI provider protocol | Medium | High |
| 3 | Scout CLI composition | `3.0-r5-cli-composition` | Move provider construction behind application-owned rollout wiring | High | High |

Each future revision migrates one consumer boundary. Planning changes require
new discovery evidence and documentation; they never mutate frozen Module 2.9.

## Compatibility policy

Every consumer migration must preserve:

- public behavior and outputs;
- request and result semantics;
- lifecycle and cleanup ownership;
- retry ownership;
- cache semantics;
- the applicable public error taxonomy.

Only the application-owned execution boundary may change. Provider identity,
registration, claim, execution-result, and lifecycle authority remain lower-owned.

## Rollback policy

Rollback is application-owned and consumer-local. It restores the previous
consumer boundary without modifying Module 2.9, provider implementations,
provider contracts, registrations, claims, or lifecycle authority. No rollback
may require a provider or authority change.

Revision 2 defines this policy; it does not claim that a concrete migration or
rollback mechanism exists yet.

## Verification policy

Every future migration requires focused migration tests, compatibility tests,
relevant regression tests, and independent verification. A migration may be
committed only after verification and tagged only after that verified commit.
No consumer becomes a permanent rollout target before those gates pass.

## Explicit non-goals

Revision 2 does not migrate a consumer, modify Module 2.9, compose or execute a
provider, construct a provider client, retrieve credentials, perform networking,
change adapters, add routing or fallback, or begin Ollama, Gemini, or Claude work.
