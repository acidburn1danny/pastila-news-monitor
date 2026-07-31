# Controlled Revision time-normalization correction

Part 5E corrects the validation-only false rejection proven by Part 5D. The
provider preserved both ordered time endpoints in one recognized alternate range,
but the required-time predicate accepted only a contiguous canonical rendering.
The editorial contract and production prompt require factual interval preservation,
not a particular separator.

## Correction

An immutable `TimeRange` stores only normalized start and end endpoints. Required
ranges and candidate expressions are parsed into this representation and compared
deterministically inside the existing targeted-component scope.

Accepted expressions are canonical dash forms after existing Unicode, whitespace,
and typographic-dash normalization, plus the explicitly approved Romanian
between/and and from/to connective forms. Matching is case-insensitive after the
existing case-folding step. Harmless punctuation adjacent to approved connectives
is supported.

Canonical parsing has precedence by expression form, and the alternate parsers do
not recognize canonical spans. Each expected range must have exactly one accepted
expression. Duplicate canonical/alternate mentions therefore fail with a safe
count-mismatch category rather than being double-counted as one range.

The following remain rejected: reversed or changed endpoints, missing endpoints,
globally separated or cross-component endpoints, unsupported connectives,
leading-zero changes, dot notation, ambiguous expressions, and duplicate ranges.
Pairing requires one recognized syntactic expression in the same targeted
component. No arbitrary global endpoint pairing occurs.

Required-time and unauthorized-time checks remain independent. Recognizing the
required interval does not remove additional configured unauthorized times from
the latter predicate.

## Diagnostics and privacy

Part 5D safe diagnostics remain intact: expected and matched range counts,
canonical and alternate counts, expected and matched endpoint counts, and unpaired
endpoint counts. No source or revised prose, actual provider output, prompt,
request/response payload, raw validation value, exception, request ID, or
credential is retained.

## Tests and replay

T01–T25 cover approved forms, rejected variants, ordering, endpoint completeness,
pairing, duplicate detection, multiple expected ranges, cross-component isolation,
unsupported connectives, unauthorized-time independence, safe errors, and
content-free serialization. One E2E-01 replay may run only under
`SCOUT_RUN_LIVE_OPENAI_PART5E=1` after every local and regression gate passes. Its
result is appended without performing a correction or second request in the same
run.

## Replay result — 28 July 2026

The one-request E2E-01 replay passed. It used one runtime attempt, one SDK request,
no retry, and no fallback. Provider DTO validation, exact reference authorization,
deterministic reconstruction, normal domain validation, gateway validation,
lineage, fingerprints, diagnostics, and privacy checks passed.

Safe time diagnostics reported one expected and matched range, one matched start
endpoint, one matched end endpoint, zero canonical matches, one approved alternate
match, and zero unpaired endpoints. The required-time predicate and complete E2E-01
aggregate both passed. Usage was 941 input tokens, 75 output tokens, and 1,016 total
tokens; duration was 11,834 ms. No prose or identifiers were emitted.

The formal Part 5 acceptance criteria require all four scenarios and exactly four
requests in one clean bounded run. Therefore the recommendation is to restart Part
5 with the corrected normalization rather than treating this isolated replay as a
partial continuation.
