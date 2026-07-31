# Editorial Script Composer — Module 2.9

Phase 1 is contract infrastructure only: it neither invokes providers nor
generates scripts. The domain foundation documents the strict construction
boundary, recursive lineage validation, provider consistency rules, and safe
revision semantics.

Shared pure invariant checks keep trusted construction, untrusted public
construction, and explicit validation consistent without executing providers
or revisions.

Phase 2 adds only deterministic input compatibility, authority conflict
detection, and representation normalization. See `Phase2InputCompatibility.md`.

Phase 3 adds immutable provider-neutral execution intent, plan, unit, request,
lifecycle, outcome, policy, binding, capability, validation, and structural
eligibility contracts. It performs no execution. See
`Phase3ProviderNeutralExecutionContracts.md`.

Phase 4.1 adds immutable draft, section, transition, reference, and structural
metadata contracts without generating text. See
`Phase4DraftStructureModels.md`.

Phases 1 through 4.2 are frozen. Phase 4.2 adds deterministic immutable claim
binding between those draft sections and normalized-input-owned claim references.
It does not generate prose, bind evidence, score coverage, or determine readiness.
See `Phase4ClaimBinding.md`.

Phase 4.3 adds deterministic section composition: an exact immutable projection of
validated binding plans into ordered composed sections and claims. It generates no
language and introduces no provider or execution behavior. See
`Phase4SectionComposition.md`.

Phase 5.1 adds deterministic semantic LLM-request composition. It projects the
frozen section-composition plan into a self-contained request plan without
rendering prompts or introducing provider and execution behavior. See
`Phase5LLMRequestComposition.md`.

Phase 5.2 adds deterministic provider-neutral prompt rendering. It projects the
frozen semantic request into canonical immutable messages and sections without
invoking providers or generating editorial language. See
`Phase5PromptRendering.md`.

Phase 5.2 status: **VERIFIED / FROZEN**.

Phase 6.1 adds provider-neutral LLM execution request planning. It projects each
validated Phase 5.2 rendered plan, section, and message one-to-one into immutable
execution eligibility contracts without provider configuration or execution. See
[`Phase6ExecutionPlanning.md`](Phase6ExecutionPlanning.md).

Phase 6.1 status: **VERIFIED / FROZEN**.

Phase 6.2 adds deterministic provider-request mapping. It maps validated Phase 6.1
plans into typed OpenAI-shaped request plans without importing an SDK, selecting
runtime inference settings, or executing a provider. See
[`Phase6ProviderMapping.md`](Phase6ProviderMapping.md).

Phase 6.2 status: **Verified — frozen**.

Phase 6.3 adds immutable provider execution-result contracts. It represents
already extracted OpenAI output with deterministic ownership, references, seals,
ordering, reconstruction, and validation. It does not execute providers or use
networking or SDKs. See
[`Phase6ProviderResults.md`](Phase6ProviderResults.md).

Phase 6.3 status: **Implemented — awaiting independent verification**.

The Module 2.9 package public API now spans the frozen Phase 1 domain foundation,
Phase 2 input compatibility, Phase 3 provider-neutral execution contracts,
Phase 4.1 draft-structure contracts, Phase 4.2 claim-binding contracts, and the
frozen Phase 4.3 section-composition and Phase 5.2 prompt-rendering contracts,
plus the Phase 5.1 and unfrozen Phase 6.1 contracts. Their stable exports and deferred
responsibilities are listed in the dedicated documents.

Phase 4.1 explicit validation treats caller-supplied objects as raw input. Each call
reconstructs fresh immutable draft and context snapshots, performs every semantic
and ownership check against those snapshots only, and retains no caller collection
or mutable lookup. It does not mutate or freeze an unvalidated `model_copy()`.

Version 1.0.0, Phase 1 implements the pure domain foundation for converting an
authoritative Module 2.8 `CompositionPlan` into a future structured
`ScriptDraft`.

Implemented in Phase 1:

- strict immutable contracts and controlled vocabularies;
- the resolved `GenerationProfile` and generation-policy snapshot;
- provider-neutral request, response, partial-response, and acceptance DTOs;
- generated text, evidence, attribution, traceability, and revision contracts;
- canonical UTF-8 serialization and semantic SHA-256 fingerprints;
- deterministic canonical identities;
- NFC text and Unicode-code-point `TextSpanReference` semantics;
- pure structural validation and machine-readable domain issues.

Phase 1 does not execute providers, assemble a draft from provider output,
derive readiness, execute revisions, persist data, or render editorial and
teleprompter output.

See [Phase1DomainFoundation.md](Phase1DomainFoundation.md) for the frozen
implementation conventions.
