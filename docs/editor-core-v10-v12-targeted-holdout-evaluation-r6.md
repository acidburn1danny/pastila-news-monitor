# Editor Core V10 V1.2 targeted R6 holdout evaluation

This independent development evaluation compares the selected R2 step-9
development parent with the R6 step-6 adapter on the frozen 12-case R6 holdout.
All twelve cases are independent `ATTRIBUTION_GRAMMAR` cases, split evenly
between petition attribution, contested draft reports, and witness attribution.

The isolated inference runtime receives only the request corpus. The answer key
is never mounted into that namespace and is supplied only to the later read-only
auditor. Inference is offline and deterministic: greedy decoding, one beam,
seed zero, a 3,072-token input ceiling, a 2,048-token generation ceiling, and a
6,268-byte decoded-response envelope. The route binds the base model, allowed
adapters, request corpus, runner, exact published R6 training-route parent,
rootfs, and CUDA driver snapshot. Git trust is limited to each source check.

The host-side audit closes every output file and inference receipt, then checks
JSON structure, identities, source bindings, EOS, and token and byte ceilings.
Its lexical pattern check and exact-target matches are diagnostics. A separate
case-by-case review compares each response with the frozen authority span for
factual fidelity, epistemic modality, attribution wording, and Romanian grammar.
Neither training loss nor an automated lexical score selects a development parent.
This is development evaluation, without training, adjudication, or promotion.

## Local evaluation result (2026-09-21)

Both isolated inference runs completed 12/12 requests with terminal EOS,
in-envelope decoded responses, and no answer-key access or optimizer activity.
The R2 and R6 inference receipts are respectively
`9f0a3a49bbac109af7ddeea1de6a3262aac915568f4738a236ca91932be6e59c`
and `f59bcff505ae2e53207961c50ad33ac88cf2236cb211ec851a9049b3055bec01`.
Their response-bundle identity is identical:
`df3f29ff37400190ddb58976b8968bc3932943bea9a4eb33d789a82e5476fa91`.
Fresh host-side structural audit identities are
`e5cbe6d9ac99b3c0e34fc55de14b1bed50e3da46b28b7c7e9de0614f1224ef08`
for R2 and `ca1d26f6fa26870b5bcd5fe221eed557c114a21bf242a89b755dc3b4c173531d`
for R6. The comparison identity is
`9c9f64606e065594d5f44537a53e1a469bb3105268eee14caa54146f82452455`.

All 12 response strings are byte-identical between candidates. In every case,
the response text reproduces the one frozen authority span exactly. Case review
found no altered facts, lost epistemic qualification, missing attribution,
or Romanian grammatical regression. The twelve spans cover four petitions,
four contested draft reports, and four witness accounts. Both candidates
preserve the source's provisional status, response/denial, and open procedure.
Exact answer-target matches are 0/12 for each candidate because the targets
are shorter editorial paraphrases; faithful source reproduction remains valid.
No R6 improvement is demonstrated. R2 step-9 remains the development parent.

The first R6 evaluation invocation stopped before model load because the local
route bound a manifest computed without the required NUL filename separator.
It left the R6 evaluation output empty. The route was corrected to the exact
adapter manifest `28c21c47d39331cc1ad16e92ac111e49a4f6176e876fbffce22ef1a5bb56c703`,
retested, and then executed successfully. The host-side lexical diagnostic was
also corrected to recognize the grammatical present-tense `respinge`; it is
not a parent-selection criterion. Its fields are named `lexical_*`, and the
auditor pins the frozen answer-key SHA-256 before reporting results.
