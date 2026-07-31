# Controlled Revision time-predicate investigation

Part 5D investigates the isolated `editorial.required_times` failure without
changing its acceptance semantics. Production runtime, provider transport, prompt,
DTO, reconstruction, domain, gateway, and contract code remain frozen.

## Static trace

The E2E scenario declares one required canonical range in
`acceptance_specification()`. `evaluate_editorial_acceptance()` selects only the
revised authorized component through `_targeted_text()`, applies
`normalize_editorial_text()`, and invokes `_required_time_result()`. The source and
revised target are compared separately for distinctness. Required general fact
markers use the complete assembled text, but the time predicate uses only the
targeted revised component.

The normalization path is Unicode NFC, non-breaking-space replacement, dash
canonicalization, case folding, whitespace collapse, and punctuation-spacing
normalization. The frozen acceptance decision remains a contiguous canonical-range
substring check. Endpoint extraction and alternate-rendering recognition are now
diagnostic only and do not affect that decision.

The expected range is present in the original targeted opening. The opening is the
only authorized E2E-01 target, and both the scenario instruction and the OpenAI
projector explicitly require preservation of factual content. Neither requires an
exact separator or literal surface form. Consequently prompt alignment is
`PROMPT_EXPLICIT`, while the predicate/contract assessment is
`FORMAT_STRICTER_THAN_CONTRACT`.

## Safe endpoint diagnostics

The time result now records only counts for expected ranges, canonical matches,
matched ranges, expected and matched start/end endpoints, recognized alternate
renderings, and unpaired endpoints. Failure categories distinguish missing starts,
missing ends, alternate renderings, unpaired endpoints, count mismatches, and safe
execution errors. No time value, prose, prompt, provider output, request ID,
credential, or exception is retained.

## Local matrix

T01–T04 verify canonical en dash, hyphen, em dash, and spaced ranges. T05–T06
recognize Romanian connective and from/to forms diagnostically while retaining the
current failing acceptance decision. T07 checks reversal; T08–T09 single endpoints;
T10 unrelated global endpoints; T11–T12 changed endpoints; T13 leading-zero
variation; T14 dot notation; T15 non-breaking spaces; T16 independent unauthorized
time detection; T17 omission; and T18 content-free extraction failure.

The current contract accepts T01–T04 and T15. Alternate connective forms are
recognized but not accepted. Endpoint reversal and globally separated endpoints
remain unpaired. Leading-zero and dot variants remain distinct. The predicate is
target-scoped, order-sensitive through canonical/alternate range recognition, and
does not use teleprompter or provider DTO text directly.

## Controlled replay

After all local, regression, privacy, and quality gates pass, one replay may run
under `SCOUT_RUN_LIVE_OPENAI_PART5D=1`. It emits only counts, categories, scope,
prompt alignment, and contract alignment. The result and evidence-based root-cause
classification are appended after that run; no correction or replay occurs in the
same execution.

## Replay result — 28 July 2026

The replay made one request with one runtime attempt, no retry, and no fallback.
Provider DTO validation, exact reference authorization, reconstruction, normal
domain validation, gateway validation, lineage, fingerprints, privacy, and safe
reporting passed. Usage was 941 input tokens, 77 output tokens, and 1,018 total
tokens; duration was 2,881 ms. Identifiers were available but not emitted.

The safe time diagnostics reported one expected range, zero canonical/matched
ranges, one matched start endpoint, one matched end endpoint, one recognized
alternate rendering, and zero unpaired endpoints. No values or prose were retained
or printed.

Root cause is `PROVIDER_PRESERVED_ENDPOINTS_WITH_ALTERNATE_RENDERING`. The provider
preserved both interval endpoints in a recognized alternate form, while the frozen
predicate accepts only the contiguous canonical form. This confirms
`FORMAT_STRICTER_THAN_CONTRACT`; the contract and prompt require preservation of
the facts, not a specific separator. The recommended next milestone is a targeted
time-normalization correction that defines and tests the allowed alternate forms.
