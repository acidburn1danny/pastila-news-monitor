# Humor Mechanics Curriculum V1 — Manifest and Evidence-Audit Specification

Status: `OWNER_APPROVED_AND_FROZEN`

This specification defines the evidence infrastructure for the frozen, owner-approved
50-mechanism Humor Mechanics Curriculum V1. It does not enrich the curriculum, expose
it to a model, select mechanisms, alter prompts, integrate with Core or Voice, change
runtime behavior, or authorize training.

The canonical taxonomy manifest is
[`docs/artifacts/humor-mechanics-curriculum-v1.manifest.json`](artifacts/humor-mechanics-curriculum-v1.manifest.json).

## 1. Artifact boundary

The manifest canonically freezes:

- curriculum and mechanism identities and versions;
- five-batch ordering;
- mechanism names and primary families;
- explicit parent/subtype relationships;
- high-risk neighboring-mechanism distinctions;
- frozen mechanism-specific and curriculum-wide boundaries;
- evidence vocabularies used by the enrichment audit;
- Level 2 composition evidence requirements;
- explicit non-goals.

The manifest is specification data, not application configuration. No runtime module
may import it until a separately owner-approved integration design exists.

Frozen entries are never edited in place. A correction must create a new manifest
version and record which earlier identity it supersedes. Evidence may be appended or
re-adjudicated without changing a frozen mechanism definition.

## 2. Canonical identity

The manifest reserves `canonical_identity` for an owner-review freeze action. Compute
the identity as SHA-256 over UTF-8 canonical JSON with `canonical_identity` omitted.
Canonicalization must sort object keys, preserve array order, use JSON primitives only,
and introduce no whitespace or platform-dependent newlines. An implementation may use
RFC 8785 directly or a proven equivalent for this restricted value set.

The owner-approved manifest persists the resulting identity. Its frozen specification
binding also records the SHA-256 of this exact Markdown artifact, so the manifest and
evidence-audit specification form one authoritative evidence-specification pair.

## 3. Stable identities and versioning

Mechanism IDs follow:

```text
HMCV1-B{batch}-M{position}-{STABLE_NAME}
```

The ID identifies the frozen concept, not a prompt label. `version` uses semantic
versioning. Wording corrections that change no pedagogical meaning may increment a
patch version in a superseding artifact. Meaning, boundaries, or parentage changes
require at least a minor version and renewed owner approval.

Every mechanism evidence record references the exact mechanism ID and version. Names
alone are never sufficient joins.

## 4. Parent, subtype, and distinction semantics

`parent_id` and `relation_to_parent` record actual subtype relationships. Embedded
subtypes such as Bathos, anti-proverb, reductio ad absurdum, and interface parody remain
inside their approved parent entry and do not increase the count beyond fifty.

`distinguish_from` is an audit hint, not an assertion of mutual exclusion. One surface
may legitimately instantiate several neighboring mechanisms. Evidence annotators must
not force a single label merely because the manifest supplies one primary family.

## 5. Evidence record contract

Each candidate example, anti-example, or composition proof must produce one immutable
evidence record with this logical shape:

```json
{
  "evidence_id": "stable unique identity",
  "evidence_version": "1.0.0",
  "provenance_class": "OWNER_FINAL_HISTORICAL",
  "source": {
    "story_id": "optional governed story identity",
    "episode_id": "optional episode identity",
    "source_artifact_identity": "required for historical evidence",
    "source_char_range": [0, 42],
    "source_utf8_byte_range": [0, 44],
    "source_sha256": "sha256 hex",
    "commentary_exact": true
  },
  "factual_context": {
    "authority_identity": "optional for synthetic pedagogical evidence",
    "summary_identity": "optional for synthetic pedagogical evidence",
    "summary_byte_immutable": true,
    "current_authority_compatibility": "COMPATIBLE"
  },
  "surface": {
    "language": "ro",
    "text": "exact example or anti-example",
    "text_sha256": "sha256 hex"
  },
  "mechanism_annotations": [],
  "semantic_domains": [],
  "syntactic_metadata": {},
  "attractor_annotations": [],
  "negative_annotations": [],
  "owner_review": {},
  "training_eligibility": "NOT_ADJUDICATED"
}
```

This specification intentionally does not create these records yet.

## 6. Provenance classes

The seven manifest classes are mutually exclusive at the record level:

- `OWNER_FINAL_HISTORICAL`: byte-exact owner-final historical material.
- `OWNER_ACCEPTED_PRODUCTION`: output explicitly accepted through a governed production proof.
- `OWNER_APPROVED_SYNTHETIC_PEDAGOGICAL`: constructed teaching material approved as curriculum evidence, never historical voice.
- `DERIVED_CONTRASTIVE_NEGATIVE`: deliberately constructed near-miss or failure tied to a positive or rule.
- `MODEL_GENERATED_UNAPPROVED`: model output with no owner voice authority.
- `EXCLUDED_FACTUAL_BOUNDARY_FAILURE`: retained only as negative evidence of a hard factual failure.
- `EXCLUDED_REALIZATION_QUALITY_FAILURE`: fact-safe or otherwise valid-shaped material rejected for humor or voice quality.

No process may relabel synthetic pedagogy as historical owner voice. Editing a historical
surface creates a derived record with new provenance; it cannot retain byte-exact status.

## 7. Mechanism annotations

Each annotation contains:

```json
{
  "mechanism_id": "HMCV1-B01-M03-CONTRAST_JUXTAPOSITION",
  "mechanism_version": "1.0.0",
  "role": "DOMINANT",
  "confidence": "OWNER_CONFIRMED",
  "evidence_span": [0, 24],
  "rationale": "short owner-readable explanation"
}
```

Allowed roles are `DOMINANT`, `SUPPORTING`, `DELIVERY`, `COMPOSITION`, and
`RESTRAINT`. A record may have no dominant mechanism when the accepted result is
serious reset, no commentary, or abstention. Multiple dominant labels require explicit
owner rationale and should be rare; the contract does not forbid them.

Annotations are post-hoc evidence. They are not model-visible instructions or runtime
selection receipts.

## 8. Factual compatibility

Historical owner-final voice and current Core V1.2 authority are different axes.
`current_authority_compatibility` must be one of:

- `COMPATIBLE`
- `COMPATIBLE_ONLY_AS_NONFACTUAL_EXCERPT`
- `INCOMPATIBLE_FACTUAL_RECAP`
- `INCOMPATIBLE_ALLEGATION_OR_UNCERTAINTY`
- `INCOMPATIBLE_UNSUPPORTED_CAUSALITY_INTENT_OR_STATUS`
- `NOT_ADJUDICATED`

An authentic historical example may be curriculum-relevant while remaining ineligible
for current training. Style authenticity never waives factual authority.

## 9. Semantic-domain metadata

Records use one or more manifest domain IDs. The audit must measure distribution across
the entire curriculum and per mechanism. It must flag concentration in administrative
process, clarification, product update, application, premium service, meeting, and
public-announcement stories.

The audit must seek evidence across the declared domains without filling quotas through
weak, duplicated, or synthetic examples. `SERIOUS_PROTECTED_SUBJECT_RESTRAINT` is used
primarily for target discipline, serious reset, and abstention evidence.

## 10. Syntactic-diversity metadata

Every Romanian surface receives:

- sentence shape;
- grammatical person;
- cadence;
- turn position;
- surface form;
- token and sentence counts;
- opening and closing normalized n-grams;
- optional cadence signature;
- Romanian naturalness adjudication.

Naturalness states are:

- `OWNER_ACCEPTED_NATURAL`
- `REVIEWER_ACCEPTED_NATURAL`
- `QUESTIONABLE`
- `TRANSLATED_OR_FORCED`
- `NOT_ADJUDICATED`

Zeugma and familiar-expression evidence cannot pass on technical classification alone;
idiomatic spoken Romanian is a hard quality requirement.

## 11. Attractor audit

Attractor annotations use the six manifest categories and include:

```json
{
  "category": "SYNTACTIC_ATTRACTOR",
  "signature": "NU_E_X_E_Y",
  "scope": "CROSS_MECHANISM",
  "severity": "REVIEW",
  "matched_evidence_ids": []
}
```

The audit must inspect exact and normalized recurrence of:

- lexical openings and closings;
- syntactic skeletons;
- frame types;
- source domains;
- cadence sequences;
- landing operations;
- abstract subjects paired with repeated personifying predicates.

An attractor flag triggers review; it is not an automatic rejection threshold. Comic
Naming receives an additional audit for systematic program names, acronyms, headings,
and capitalization. Aphoristic Compression receives an additional audit for generic
quote-card and slogan language.

## 12. Negative-example contract

Each negative record has at least one manifest negative class and separately records:

- factual status;
- protected-subject and target status;
- mechanism-realization status;
- Romanian naturalness;
- story specificity;
- attractor risk;
- whether repair is permitted;
- the exact boundary or quality rule demonstrated.

Near-miss coverage is mandatory in the enrichment design. It must include fact-safe but
generic output, mechanism confusion, wrong dominant labels, technically valid but
unnatural Romanian, weak tags, overcomposition, fiction that sounds factual, historical
voice incompatible with current authority, and Serious Reset false positives and false
negatives.

Negative text is never silently repaired and presented as owner-final. A repair creates
a new derived record linked by `derived_from_evidence_id`.

## 13. Level 2 composition evidence

Level 2 teaches interactions, not combinations to memorize. Its evidence records use
the same factual context and compare multiple realizations without asserting one correct
mechanism choice.

### 13.1 Mechanism-preserving transformations

Required proof shapes include:

- same editorial point, different mechanism;
- same mechanism, different syntax and cadence;
- one supporting mechanism removed;
- an overbuilt composition reduced to one mechanism;
- named realization replaced by an unnamed observation;
- same landing expressed without a repeated frame.

### 13.2 Same-story alternatives

Where defensible, a story family should contain:

- a valid single-mechanism realization;
- a different valid single-mechanism realization;
- a restrained multi-mechanism realization;
- a fact-safe but generic negative;
- an overcomposed negative;
- no humor, serious reset, or abstention.

These are evidence shapes, not quotas. A story must not be forced to support all options.

### 13.3 Pairwise graph

Composition evidence must form a connected mechanism-pair graph without dominant hubs
or preferred story-to-pair mappings. It must contain coherent unexpected pairs, pairs
that should not be combined for the fixture, and owner-approved subtraction examples.
Some valid pairs remain entirely held out.

### 13.4 Dominant and supporting roles

Every multi-mechanism positive identifies what each mechanism contributes and whether
removal changes the result. Mechanism density is never a quality target.

### 13.5 Three-plus composition

High-density positives are introduced only after pairwise evidence. The audit requires
more overcomposition near-misses than high-density positives. Visible seams, excessive
length, factual risk, and failure to stop are explicit rejection reasons.

### 13.6 Free choice and holdout

Free-choice fixtures expose no mechanism label to the model. Their mechanism annotations
are post-hoc sidecars. Holdouts cover unseen pairs, triples, semantic domains, syntactic
families, frames, landings, and serious-reset decisions.

Current story-local authority remains in force. Cross-story Callback, Bookending, and
Running Gag evidence is pedagogical-only and cannot be promoted to current runtime or
training eligibility.

## 14. Audit outputs required before enrichment can be accepted

The future enrichment phase must produce, without changing this manifest:

1. a provenance ledger;
2. a mechanism-annotation ledger;
3. a factual-compatibility ledger;
4. semantic-domain coverage report;
5. syntactic and Romanian-naturalness report;
6. attractor report;
7. negative-example coverage matrix;
8. Level 2 pair graph and holdout declaration;
9. historical-versus-synthetic coverage report;
10. owner-review queue containing all unresolved adjudications.

No aggregate score may hide a hard factual failure. Historical count, mechanism count,
and taxonomy coverage are descriptive, never quotas.

## 15. Readiness states

Evidence packages use these ordered states:

- `SPECIFICATION_ONLY`
- `EVIDENCE_COLLECTION_IN_PROGRESS`
- `OWNER_REVIEW_REQUIRED`
- `CURRICULUM_ENRICHMENT_EVIDENCE_ACCEPTED`
- `PROMPT_EXPOSURE_DESIGN_ELIGIBLE`
- `WEIGHT_TRAINING_DESIGN_ELIGIBLE`

This artifact remains `SPECIFICATION_ONLY` and is frozen as the authoritative evidence
specification for the next enrichment phase. Later readiness states require separate
owner actions.
Acceptance of enrichment evidence does not itself authorize prompt exposure, runtime
integration, or training.

## 16. Explicit non-goals

This specification does not authorize or perform:

- curriculum enrichment;
- historical-example extraction;
- synthetic-example generation;
- mechanism annotation of new records;
- application packaging;
- Core or Voice integration;
- retrieval or routing;
- prompt changes;
- model changes;
- runtime changes;
- cross-story authority expansion;
- training or dataset construction.
