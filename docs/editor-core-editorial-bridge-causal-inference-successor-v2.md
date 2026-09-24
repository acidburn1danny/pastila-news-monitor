# Editorial Mechanics Bridge causal inference successor v2

## Scope

This successor replaces inference authority v1 only for the seven synthetic development candidates. It does not authorize training, holdout access, human scoring, parent selection, adjudication, promotion, or release.

## CAR

- **Root cause:** R2 and all three A2 adapters entered the same deterministic repetition loop for `ec-bridge-v1-qualified-compression-09`. Generation reached the existing 2,048-token ceiling inside the JSON `text` string. The request and adjacent qualified-compression cases were structurally sound. Increasing the ceiling would only prolong the loop and is not a repair.
- **Impact:** four of 168 rows lacked terminal EOS and were invalid JSON. Authority v1's auditor exposed `all_terminal_eos=false` but still returned `verdict=PASS`; the supervisor consequently prepared ineligible scoring packets. Its exception wrapper also treated normal `SystemExit(0)` as a second terminal BLOCKED event.
- **Repair:** v2 applies the same deterministic eight-token no-repeat constraint to every candidate, targeting the demonstrated repetition loop without increasing the 2,048-token ceiling or changing qualification semantics. It validates terminal EOS, strict JSON, exact top-level key order, duplicate-key absence, and request binding before writing any candidate output. The independent auditor repeats those checks and requires exactly 24 EOS rows per candidate and 168/168 overall. The supervisor emits exactly one terminal event and prepares scoring packets only after inference audit PASS. Authority v2 rejects all v1 inference packages and binds every successor source byte.
- **Closure:** fixture and adversarial tests cover truncation, malformed JSON, duplicate keys, request substitution, historical-output rejection, terminal-log single assignment, authority identity, source hashes, and unpublished-source rejection.

## Historical evidence

The v1 inference outputs and their derived 72 primary, 24 reference, and custody artifacts remain historical failure evidence. They are not eligible for human scoring and must not be reused by v2. Successor execution must use new empty output and scoring roots.

## EOS reconciliation

The authoritative observations record four non-EOS rows: the same case under R2 and the three A2 seeds. The exact closure is therefore 164/168 EOS. The earlier `162/168` statement and “six responses” count were reporting arithmetic errors, not additional rows or missing artifacts.
