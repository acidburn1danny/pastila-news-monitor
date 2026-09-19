# V15 R4 read-only adjudication boundary

This successor boundary consumes only the completed, immutable R4 evidence at
`/root/pf9-v15-r4-preconsumption-output`. It validates the published R4 source and
execution authority, the atomic attempt, all 2,400 scheduled rows, all completion
inventory bytes, and the completion identity before deriving a candidate-blinded
adjudication input root.

The frozen evidence contains 1,986 structurally valid rows eligible for human
semantic receipts and 414 rows already classified fail closed for invalid output.
The boundary preserves both classes and never upgrades a structural failure.

The boundary does not emit a semantic verdict. A verdict requires two distinct
owner-registered human adjudicators to sign receipts over the exact same blinded
row authority. Only two authenticated `PASS` receipts can pass; missing,
mismatched, invalid, indeterminate, or disagreeing receipts fail closed. Candidate
identity disclosure, attempt mutation, execution, retry, redraw, and promotion are
outside this boundary.
