# OpenAI Controlled Revision provider DTO ownership review

## Ownership principles

The OpenAI provider may author only prose for invocation-targeted components. The
invocation owns scope, required references, instruction authority, preservation, and
output obligations. The source draft owns identities, structure, ordering, protected
content, and CTA metadata. The interpreter maps references and validates the exact
returned set. The domain derives aggregate text and validates invariants. Gateway
factories compute lineage projections and result identity.

## Complete ownership matrix

| Field path | Type | Owner | Visible/returned | Editable | Authority and validation | Reconstruction | Status |
|---|---|---|---|---|---|---|---|
| `revised_components` | array, 1–50 | PROVIDER_AUTHORED container | yes/yes | n/a | DTO length and uniqueness | Exact-set mapped | CORRECT |
| `*.component_type` | strict literal | INVOCATION_AUTHORITATIVE tag echoed for union selection | yes/yes | no | DTO checks type/reference form; reconstructor checks reference scope | Selects patch shape only | CORRECT |
| `*.component_reference` | bounded string/literal | INVOCATION_AUTHORITATIVE lookup echoed by provider | yes/yes | no | Canonical projector generation, DTO syntax, exact-set authorization | Maps to one source component | CORRECT — JUSTIFIED REFERENCE |
| text component `revised_text` | bounded nonempty string | PROVIDER_AUTHORED | yes/yes | yes | DTO; invocation reference determines opening/transition/closing | Replaces only targeted prose | CORRECT |
| story `factual_summary` | bounded nonempty string | PROVIDER_AUTHORED | yes/yes | yes for a story target | DTO plus story-target authorization | Applied to authoritative story | CORRECT |
| story `commentary_block_texts` | bounded string array | PROVIDER_AUTHORED | yes/yes | yes for a story target | DTO; count must equal authoritative blocks | Texts applied to source block metadata | CORRECT |
| story `ending` | bounded nonempty string | PROVIDER_AUTHORED | yes/yes | yes for a story target | DTO plus story-target authorization | Applied to authoritative story | CORRECT |
| CTA `bridge_text` | bounded nonempty string | PROVIDER_AUTHORED | yes/yes | yes for CTA target | DTO plus exact reference | Applied to source CTA | CORRECT |
| `episode_id` | string | SOURCE_DRAFT_AUTHORITATIVE | no/no | no | DTO forbids it; EpisodeDraft validates locally | Copied from source | CORRECT |
| story IDs | integer | SOURCE_DRAFT_AUTHORITATIVE | encoded only in lookup reference | no | Exact-set mapping; provider cannot return an ID field | Copied from source | CORRECT |
| transition endpoints | integer pair | SOURCE_DRAFT_AUTHORITATIVE | encoded only in lookup reference | no | Exact-set mapping to existing transition | Copied from source | CORRECT |
| component ordering | sequence | SOURCE_DRAFT_AUTHORITATIVE | no/no | no | No position/order DTO fields | Source list positions retained | CORRECT |
| protected component content | domain values | SOURCE_DRAFT_AUTHORITATIVE | no/no | no | Non-target references rejected | Copied from source | CORRECT |
| CTA placement/static content | domain values | SOURCE_DRAFT_AUTHORITATIVE | no/no | no | Absent from DTO | Copied from source | CORRECT |
| `assembled_text` | string | DOMAIN_COMPUTED | no/no | no | Existing derivation and EpisodeDraft validator | `derive_assembled_text` | CORRECT |
| `teleprompter_text` | string | DOMAIN_COMPUTED | no/no | no | No revision target; formatting is downstream | Baseline regenerated from assembly | CORRECT |
| source/invocation lineage | fingerprints | INVOCATION_AUTHORITATIVE | no/no | no | Existing invocation and gateway validation | Projected by interpreter/factory | CORRECT |
| contract metadata | typed contract | INVOCATION_AUTHORITATIVE | input obligations only; not returned | no | Existing output contract | Never read from provider output | CORRECT |
| draft/component fingerprints | hashes | DOMAIN_COMPUTED | no/no | no | Existing fingerprint algorithms | Recomputed from domain state | CORRECT |
| gateway/result identity | hashes and versions | GATEWAY_COMPUTED | no/no | no | Existing gateway factory and validators | Computed after reconstruction | CORRECT |

The provider DTO has twelve distinct field paths across its root and three component
variants. All are classified. No returned field has mixed ownership.

## DTO and component references

References are generated from frozen targets as `opening`, `closing`,
`call_to_action`, `story:<positive-id>`, or
`transition:<positive-from-id>:<positive-to-id>`. Syntax is case-sensitive and
whitespace-sensitive; aliases and Unicode normalization are not accepted. Numeric
forms are canonical Python integer rendering, so two source components cannot collide.

The provider echoes a reference only as a lookup token. DTO validation rejects
duplicates and malformed type/reference combinations. Reconstruction compares the
returned set exactly with invocation targets, classifies unknown versus protected
references, rejects missing targets, and applies edits by authoritative source
position. Provider order is ignored. Dynamic schema enums are unnecessary because
the local exact-set check is deterministic and already fail-closed.

`component_type` is a justified strict-union tag, not an authorization decision. It
cannot disagree with the reference family under DTO validation.

## Component review

- Opening and closing: only targeted prose is provider-authored.
- Story: a story target authorizes its prose fields as a unit. Story ID, position,
  commentary-block metadata, and structure remain source-owned. Returned block text
  count must match the authoritative blocks.
- Transition: only prose is returned. Endpoints, adjacency, identity, and order come
  from the source transition selected by the authorized reference.
- CTA: only bridge prose is editable. Placement, static content, ordering, and CTA
  existence remain authoritative. A CTA cannot be inserted when absent.

## Teleprompter ownership

Classification: DOMAIN_COMPUTED.

Initial assembly sets teleprompter text from canonical assembled text. The controlled
generator may apply specialized deterministic formatting later. Controlled Revision
has no teleprompter target or independent provider-owned teleprompter contract.
Allowing the provider to return it would create two prose authorities. Reconstruction
therefore regenerates the canonical baseline; specialized formatting remains a later
pipeline responsibility.

## Prompt, schema, and interpreter alignment

The projector asks for exactly one edit per supplied targeted reference, forbids
complete episode state and derived text, and supplies only targeted source data under
an explicit untrusted-data classification. The strict schema contains exactly the
provider DTO. The interpreter validates that DTO before reconstruction. The
reconstructor expects the exact same reference set. No ownership contradiction was
found.

Expected-output obligations remain provider-visible input context but cannot be
returned or overridden. They remain invocation-authoritative and are used locally by
the gateway boundary.

## Reconstruction review

Reconstruction begins with the source draft, maps each authorized patch, preserves
all list positions and structural metadata, computes assembled text with the existing
domain function, constructs `EpisodeDraft` normally, and delegates gateway identity
to the existing factory. It neither uses `model_construct` nor duplicates adjacency,
uniqueness, fingerprint, or lineage algorithms.

## Findings and changes

No ownership finding was established. `component_reference` and `component_type` are
small justified mapping fields rather than removable or dangerous duplication.

No production changes were required. One parameterized test now proves that sixteen
identity, ordering, lineage, contract, derived, and protected field categories are
rejected at the nested DTO boundary.

## Regression and readiness

The review made no live request. Focused tests, the full suite, Ruff, Black,
compileall, and dependency validation passed. The ownership boundary is confirmed
and Part 5 may resume.
