# Phase 5.2 — Deterministic Prompt Rendering

## Architecture and responsibility

Phase 5.2 transforms one validated Phase 5.1 `DraftLLMRequestPlan` into an
immutable `DraftRenderedPromptPlan`:

`Phase 5.1 semantic request → Phase 5.2 canonical rendering → future execution`

It owns textual rendering, canonical delimiters, LF line endings, whitespace,
ordering, rendering lineage, validation, identities, and fingerprints. It does
not invoke an LLM, communicate with a provider, generate editorial language, or
parse a response.

## Public contracts and API

The public models are `RenderedPromptMessage`, `RenderedPromptSection`,
`DraftRenderedPromptPlan`, and `RenderedPromptValidationContext`. The context
retains authoritative Phase 5.1 plans and their frozen validation context; it
creates no duplicate authority graph.

The package exports the four models, `build_draft_rendered_prompt_plan`,
`validate_draft_rendered_prompt_plan`, and three public identity plus three public
fingerprint functions. Rendering helpers, canonical-reference derivations,
reconstruction records, duplicate collectors, and validation internals remain
private.

## Canonical rendering and formatting

Every request claim becomes exactly one provider-neutral `generation` message.
Its canonical text is:

```text
<request-claim>
claim-reference: <canonical claim reference>
requirement: <required-or-optional>
role: <structural role>
ordinal: <zero-based ordinal>
</request-claim>
```

Formatting is centralized and independently recomputed by validation. It uses NFC
Unicode, `\n` line endings, no trailing spaces, no indentation, no blank lines,
and fixed delimiters. Submitted text must equal the authoritative rendering
exactly; correctly resealed spacing, newline, delimiter, Unicode, or paragraph
alternatives remain invalid.

## Canonical references and seals

Private shared derivations produce and validate exactly:

- `rendered-prompt-plan:<request-plan-identity>`
- `rendered-prompt-section:<request-section-identity>`
- `rendered-prompt-message:<request-claim-identity>`

Identity includes every semantic rendering field except identity and fingerprint.
Fingerprint includes identity and every other semantic field except fingerprint.
Both reuse the frozen NFC, canonical-JSON, UTF-8, SHA-256 architecture.

## Builder and validator

The builder reconstructs fresh Phase 5.1 plan and context snapshots, invokes the
frozen Phase 5.1 validator, and projects every section and claim exactly once in
authoritative order. It never filters, repairs, sorts, invents, or executes.

The validator reconstructs fresh rendering and authority snapshots, validates
the Phase 5.1 authority, and checks references, lineage, seals, roles, exact text,
ordering, completeness, duplicates, ordinals, formatting, and the canonical empty
representation. Duplicate checks operate on tuples before lookup can hide them.

The sole empty representation is `rendered_sections=()` for an authoritative
request plan without sections. Placeholder sections and messages are invalid.

## Reconstruction and diagnostic safety

Ordinary reconstruction exceptions become bounded deterministic findings without
exception text, tracebacks, object representations, paths, memory addresses, or
unsafe caller values. Artifact and duplicate-related references share one bounded,
ASCII-safe diagnostic policy; unsafe inputs become deterministic placeholders.
`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` propagate unchanged.

The committed freeze-regression suite covers canonical-reference, delimiter,
whitespace, newline, field-order, punctuation, role, seal, completeness, malformed
authority, duplicate-safety, and complete cross-process diagnostic attacks.

## Future execution boundary

Phase 5.2 defines no provider, model, system/user/assistant/developer role, HTTP,
retry, streaming, temperature, top-p, token limit, inference, persistence,
generated output, or response behavior. Provider-neutral execution remains a
future phase.

Phase 5.2 is implemented but is not independently verified or frozen.
