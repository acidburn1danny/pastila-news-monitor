# Milestone 6C.4D — controlled generator

The controlled generator is a private, provider-independent stage after the frozen
selection, flow, editorial, commentary, and voice stages. The repository contained
no M6C.4A–C draft implementation, so this milestone introduces the missing private
draft transport/domain models while leaving every public contract unchanged.

## Execution and dependencies

`ControlledGenerator` constructs one immutable episode context and a deterministic
manifest before provider access. It calls the provider sequentially for stories in
optimized order, transitions, opening, closing, and optional CTA bridge. Assembly
and teleprompter formatting are local deterministic operations. The provider never
receives blueprint objects directly and never chooses order, policy, state, or
assembly.

Manifest IDs contain no clocks or UUIDs. Transitions depend on their two stories;
opening depends on all stories; closing depends on stories, transitions, and opening;
CTA depends transitively on accepted closing; assembly depends on all required draft
components; formatting depends on assembly. Readiness is derived from dependency
statuses.

## Prompt and validation protocol

Prompts are ordered sections, not opaque ad-hoc strings. Canonical UTF-8 JSON with
sorted keys produces stable SHA-256 fingerprints. Retry-only failure and correction
layers are absent from attempt one. Attempt three uses `MINIMAL_SAFE`, explicitly
disabling optional aggressive mechanisms in the prompt policy.

Only normalized approved title, summary, and category facts enter story contexts.
Raw articles and raw payloads are excluded. Structured provider results are validated
for local fact and intent references, satire/protected targets, word and voice
ceilings, callbacks, endpoints, opening payoffs, and required structure. This is
constraint validation, not Editorial QA.

Schema/content failures consume at most three editorial attempts. A timeout receives
one transport retry with the identical prompt and does not consume another editorial
attempt. Failed attempts never update `EpisodeGenerationState`. A structurally usable
third response with only non-fatal violations can be marked `REQUIRES_REVIEW`; factual
or protected-target failures are fatal.

## State, CTA, assembly, and formatting

Every accepted component returns a new frozen state revision. Callback anchors are
registered only with accepted stories and may execute only for declared target
components. CTA placement is deterministic and avoids immediately following a
sensitive story. Static CTA data is appended locally and is never sent out for
rewriting.

`assembled_text` is derived from opening, ordered stories, boundary transitions,
optional CTA, and closing. The teleprompter formatter changes whitespace and line
layout only, protects numeric-unit pairs such as `2.4 km`, and is idempotent.

## Operational reproducibility

Guaranteed: manifest and call order, prompt structure/content for identical inputs,
fingerprints, validation, retry policy, accepted-state transitions, assembly order,
formatting, and trace shape. External providers do not guarantee byte-identical
wording, punctuation, or sampling. This is **operational reproducibility**, not
perfect linguistic determinism.

The scripted provider supports offline responses, schema failures, provider errors,
timeouts, retry success, and call/prompt/schema/config recording. No network, API
key, persistence, parallel execution, or Editorial QA is implemented.

## M6C.4D.1 — Architectural Corrective Patch

Prompt serialization now uses one strict recursive canonicalizer for both section
content and fingerprint input. It supports JSON scalars, finite floats, enums,
mappings, ordered sequences, deterministically sorted sets/frozensets, Pydantic
models, and dataclasses. Unknown opaque objects and non-finite floats fail explicitly;
there is no `str`/`repr` fallback. Set members are sorted by their own compact
canonical JSON, giving stable UTF-8 prompt bytes across processes and hash seeds.
Approved facts and forbidden claims are treated as contractually unordered; story
and flow sequences remain order-sensitive.

`EpisodeGenerationState` now stores story summaries as sorted immutable record
tuples. Callback anchors and every other exposed collection are immutable tuples of
scalars or frozen models. Mapping inputs are normalized defensively, and every
accepted update creates a new revision without changing the prior state.

Static CTA material is local-only. A narrow `ProviderSafeCTAPlacement` contains only
placement metadata and is used by closing and CTA-bridge prompts, including retries.
The configured static block is added only to the local `CallToActionDraft`, assembly,
and teleprompter result.

`derive_assembled_text` is the shared authoritative assembly function. Both
`DraftAssembler` and `EpisodeDraft` validation use it. Direct construction,
deserialization, or validated copying with divergent `assembled_text` is rejected;
valid serialization continues to include the derived field for compatibility.

Operational reproducibility still covers prompt bytes/fingerprints, validation,
state transitions, assembly, and formatting—not byte-identical external-provider
wording. Retained limitations: `ApprovedFact.value` does not semantically prove its
provenance; provider configuration remains in the broad generation models module;
there is no semantic NLP verification or production provider adapter.
