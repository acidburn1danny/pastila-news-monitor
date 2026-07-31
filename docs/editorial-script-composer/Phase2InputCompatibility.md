# Module 2.9 Phase 2 Input Compatibility and Authority

Phase 2 adds a pure compatibility envelope around the frozen Phase 1
contracts. It does not change Phase 1 models and performs no generation,
provider execution, prompt construction, revision execution, rendering,
persistence, networking, or readiness derivation.

`GenerationInputBundle` groups the artifacts that must be assessed together.
`validate_generation_input_bundle()` returns a deterministic
`CompatibilityResult` containing stable `DomainValidationIssue` values and an
immutable `AuthorityConflictSet`. Conflicts are reported and never resolved.
`require_compatible_generation_input()` provides the strict typed boundary;
`construct_compatible_generation_input()` applies the same compatibility rules
after safe public construction.

Validation covers required inputs, duplicate and conflicting authorities,
profiles, policies, provider requests, instructions, constraints and decisions,
unknown custom definitions, authority-level compatibility, revision snapshot
compatibility, composition-input references, and duplicate authoritative
evidence. Every embedded Phase 1 artifact is recursively validated through the
frozen Phase 1 validator before Phase 2 compatibility is evaluated. Provider
requests must identify an included profile and its exact fingerprint. Custom
definitions must cite included authority artifacts.

`normalize_generation_input_bundle()` performs representation-only
normalization. Exact duplicates are removed, collections are ordered by stable
identities and fingerprints, and conflicting artifacts remain present for
validation. Invalid nested artifacts are rejected before normalization. A
complete deterministic artifact key resolves representation collisions, so
input order can never select a different representative. It never rewrites
semantic content.

Authority conflicts carry immutable artifact, target, field-path, and relevant
authority context. Their identifiers include that context, and duplicate
logical conflicts collapse deterministically. Merely sharing a target does not
make distinct instructions incompatible, and differing constraint values are
not contradictions without an explicit structured cross-reference prohibition.

Custom instruction and constraint definitions use `custom:<slug>` identifiers.
They authorize only matching custom references and do not expand the frozen
Phase 1 instruction or constraint type vocabularies.
