# Semantic Admission V2 — Gate F V2.5 candidate and zero-inference verification

## Outcome

The evaluation-only V2.5 candidate is complete. Its zero-inference preflight passed after a preserved fixture attempt demonstrated that span membership is byte- and case-exact.

No executor was invoked, no model was loaded, and no inference or provider call occurred.

## Candidate delta

V2.5 composes the frozen V2.4 proposition-and-scope contract with a versioned residual addendum. It adds:

- matched-event comparison across certainty/modality, timing, and status before open-class labeling;
- negative evidence requirements before causality or motive may be emitted;
- grouping of multiple authority-axis mutations belonging to one core proposition;
- deterministic decisive-versus-supporting discipline;
- exact source-side grounding for `candidate_span` and `authority_support`.

The model, constrained grammar, reason-code namespace, factual authority, precedence, and Gate S remain unchanged.

## Span validation

The evaluation-only post-parse validator applies the unchanged strict response model, then checks:

- every non-null `candidate_span` occurs exactly and contiguously in candidate commentary;
- every non-null `authority_support` occurs exactly and contiguously in factual authority.

It performs no trimming, normalization, repair, substitution, or reason relabeling. Cross-source or case-mismatched text fails closed. Semantic sufficiency of a source-valid span remains model-evaluated; deterministic validation claims membership only.

## Zero-inference evidence

- V2.5 evaluator identity: `013aa806bc058777685665bf74d0f593de649f877deea1b4d127b85986e4b60b`.
- V2.5 composed prompt identity: `sha256:c6ad791171ab2d058977779f0d669906d52cf1c80c3d7c972b07b434ab507f6a`.
- Ten exact frozen requests and rendered prompts were bound.
- The unchanged constraint accepts the required three-reason Case 10 structure.
- Valid candidate/authority membership passed; a cross-source span failed closed.
- Gate S identities are unchanged.
- Executor/model/provider calls: zero.

## Preserved failed fixture attempt

The first preflight fixture supplied lowercase `în 2027` against authority text beginning with uppercase `În 2027`. The validator rejected it exactly as designed before executor construction. The fixture was corrected to the exact source bytes and the complete preflight passed. Neither attempt performed inference.

## Authority boundary

No model probe, runtime, production, Gate S, curriculum, or training authority is granted.

## Recommended next step

After owner review, separately authorize the same two-case Gate F-only probe—Cases 01 and 10—exactly once. Require Case 01 exact PASS and Case 10 certainty DECISIVE, timing SUPPORTING, life-stakes SUPPORTING, no causality/motive, and source-valid spans before any ten-case run.
