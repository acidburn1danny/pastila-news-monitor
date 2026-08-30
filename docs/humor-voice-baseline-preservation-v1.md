# Humor Mechanics / Voice baseline preservation V1

Status: `SOURCE_AND_EVIDENCE_BASELINE_ONLY`

This record classifies the Humor Mechanics and Voice material present in the working
tree when the Case 01 work closed. It grants no runtime, prompt, model, training,
production-routing, generation, or integration authority.

## Canonical preservation set

The preservation commit contains only:

- the frozen 50-mechanism curriculum manifest and its evidence-audit specification;
- the two source builders that define the Batch 1 historical and diagnostic packs;
- focused tests for curriculum structure, identity, authority isolation, specification
  binding, and Voice import-boundary collection-order safety.

The previously committed specificity-contrast pack and final owner-accepted Voice V2
release remain referenced baselines; their bytes are not duplicated here.

The historical and diagnostic evidence packs remain byte-exact but untracked because
repository policy prohibits committing generated data. Their manifests and artifact
hashes were verified during this audit. The diagnostic `hidden-evaluation-key.json`
also remains deliberately untracked and undisclosed.

## Exhaustive classification rules for remaining untracked material

Every Humor/Voice-related untracked path outside the canonical preservation set is
classified by the first matching rule below:

1. A path containing `failed`, `superseded`, `blocked`, `attempt`, `launch`, or a
   temporary-directory marker is historical or transient evidence and is excluded from
   the canonical baseline.
2. An untracked `.pastilaacida-voice-*` evidence directory is deferred Voice evidence.
   It remains untouched and requires a separate lineage-specific preservation review.
3. An untracked Humor runner/finalizer or Voice/EEUP script, test, fixture, document, or
   generated evidence pack is active or historical
   work outside the 50-mechanism baseline and is deferred unchanged.
4. Cache, build, installer-stage, and generated runtime material is reproducible output
   and is excluded.
5. No untracked path is deleted or silently promoted by this preservation action.

At audit time, Git reported 277 Humor/Voice-related untracked status entries. This
rule set covers all of them while preventing a bulk-add of mixed authority levels.

## Evidence maturity

- Curriculum taxonomy: 50/50 mechanisms frozen.
- Batch 1 mechanism references in curriculum evidence: 10/10.
- Batches 2-5 mechanism references in curriculum evidence: 0/40.
- Batch 1 historical evidence: 13 included records from a 19-record source universe.
- Latest Batch 1 diagnostic: 18 attempts, 13 exact generated contracts, five justified
  abstentions, three runtime admissions, and one owner-quality candidate.
- Latest diagnostic lifecycle: `FIXPACK_AND_RUN5_COMPLETE_OWNER_REVIEW_REQUIRED`.

The forty mechanisms in Batches 2-5 therefore remain taxonomy-only. Their presence in
the manifest must not be represented as evidence completion or runtime eligibility.

## Frozen authority boundary

The 50-mechanism curriculum remains specification and evaluation data. It is not model
input, application configuration, a selection algorithm, or production routing. Any
Batch 2-5 evidence program, curriculum exposure, training, or runtime integration
requires a separate owner decision and a new bounded lineage.
