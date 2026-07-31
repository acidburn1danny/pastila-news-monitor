# OpenAI Controlled Revision editorial acceptance diagnostics

Part 5C replaces the Part 5 harness's opaque final Boolean with immutable,
content-free predicate results. It changes validation infrastructure only; the
provider DTO, runtime, reconstruction, domain validators, gateway, retry policy,
and editorial contract remain unchanged.

## Status and aggregation

Every stable predicate identifier has one status: `PASS`, `FAIL`,
`NOT_APPLICABLE`, or `NOT_RUN`. A predicate exception becomes `NOT_RUN` with the
category `predicate_execution_error`; raw exceptions are discarded. The aggregate
passes only when every required predicate is `PASS` or `NOT_APPLICABLE`. It is
computed exclusively from the recorded results.

The inventory covers workflow identity and authorization; gateway lineage,
fingerprints, and output contract; required facts, numbers, dates, times, and
entities; unexpected numbers, known dates, known times, known entities, quote
markers, forbidden terms, and structure; Romanian-language markers; distinct
revision; protected components; locally derived assembled and teleprompter text;
source-authority boundaries; and individual privacy categories.

Diagnostics retain only predicate IDs, statuses, canonical failure categories,
required/informational classification, and non-sensitive counts. They never retain
source or revised prose, prompts, raw payloads, raw validation values, exceptions,
credentials, or request identifiers.

## Normalization

Comparison uses Unicode NFC and case folding, converts non-breaking spaces to
ordinary spaces, collapses repeated whitespace, normalizes en dash, em dash,
minus, and non-breaking hyphen to ASCII hyphen, and removes harmless spacing around
punctuation. It does not remove digits, letters, dates, times, or factual tokens.
Consequently `120` remains distinct from `12`, `15 septembrie` from
`16 septembrie`, and `Brașov` from `București`.

The deterministic Romanian rule requires at least two distinct Romanian function
word markers from: `și`, `cu`, `de`, `va`, `fi`, `la`, `o`, `în`, `pentru`.
Normalization is applied first. Diacritics alone are not treated as language
proof, avoiding the previous fixture-word false positive. This is a harness
implementation diagnostic, not an editorial contract change.

## Coverage boundary

Covered detection is deliberately bounded: exact normalized required markers,
numbers, configured date/time variants, configured known entities, quote markers,
forbidden phrases, component counts, identities, ordering, references, and
fingerprints. It does not claim to detect subtle causal implications, semantic
exaggeration, tone distortion, unknown common nouns, or arbitrary entities absent
from the fixture's deterministic lists.

## Local reproduction matrix

The focused suite exercises D01 valid output; D02 missing number; D03 missing date;
D04 missing time; D05 missing entity; D06 unexpected number; D07 unexpected date;
D08 unexpected time; D09 unexpected entity; D10 language failure; D11 identical
revision; D12 protected modification; D13 predicate exception; D14 simultaneous
failures; and D15 non-applicable authority predicates. It also verifies typography
normalization and sanitized JSON.

## Replay

The one-request Part 5C replay uses only:

```powershell
$env:SCOUT_RUN_LIVE_OPENAI_PART5C='1'
.\.venv\Scripts\python.exe scripts\validate_openai_controlled_revision_e2e.py
Remove-Item Env:SCOUT_RUN_LIVE_OPENAI_PART5C
```

The older Part 5 flags do not trigger this replay. The replay has one attempt, SDK
automatic retries disabled, no fallback, and prints each predicate without prose.
## Replay result — 27 July 2026

The replay made exactly one request and stopped. It used one runtime attempt, one
SDK request, no retry, and no fallback. Transport, provider DTO validation, exact
reference authorization, deterministic reconstruction, normal `EpisodeDraft`
validation, gateway validation, identity, lineage, fingerprints, output contract,
provider metadata, and privacy checks passed.

Exactly one predicate failed:

- `editorial.required_times`: `FAIL`, category `required_time_missing`, expected
  count 1, matched count 0.

Every other applicable predicate passed. The three source-authority predicates
were correctly `NOT_APPLICABLE`. Usage was 941 input tokens, 84 output tokens, and
1,025 total tokens; duration was 17,959 ms. Provider request and returned-model
identifiers were available but were not printed.

This isolates the failed predicate but not its underlying cause. The current time
predicate normalizes dash variants, non-breaking spaces, and punctuation spacing,
but requires the normalized range to be contiguous. Because neither prose nor
endpoint-level diagnostic counts are retained, the evidence cannot distinguish a
missing range from a fact-preserving connective rendering of both endpoints. The
next step is a targeted acceptance-diagnostic correction that safely records
expected and matched endpoint counts. Only that evidence can justify a prompt,
normalization, model-reliability, or contract correction before Part 5 resumes.
