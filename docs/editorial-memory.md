# Editorial Memory

Editorial Memory learns stable preferences from the Editor-in-Chief's verdicts. It
stores immutable observations, detects recurring findings across distinct episodes,
and derives a versioned editorial profile. It does not edit drafts, generation
prompts, benchmarks, or the Editorial Knowledge Base.

## Processing boundary

`VerdictInput` supports an overall score, granular section scores, and one or more
comments. The deterministic interpreter emits observations only when a comment has
both a recognized editorial category and explicit positive or negative language.
Unclassified and neutral comments are preserved in the verdict input but do not
become inferred preferences.

Observation identities are deterministic hashes of episode, timestamp, original
comment, and normalized finding. Reprocessing the same verdict is therefore
idempotent.

## Learning policy

- One distinct episode creates an observation only.
- Two episodes create an emerging trend.
- Three distinct episodes establish a profile strength or weakness and make a
  candidate finding eligible.
- Candidate recommendations remain advisory. They never update a prompt.
- Confidence depends on distinct supporting episodes and is capped at 100.
- Profile versions advance only when the derived strengths, weaknesses, or trends
  change.

The thresholds are named constants in the processor and deliberately conservative.
Evidence remains inspectable through episode and observation identifiers.

## Persistence

`load_memory` and `save_memory` provide strict Pydantic validation and atomic UTF-8
JSON snapshots. Missing files produce an empty schema-versioned memory. Persistence
is explicitly invoked by callers; importing or processing a verdict performs no
filesystem writes.
