# Semantic Admission V2 — constrained Run 4 report

## Outcome

Run 4 completed exactly once in the unrestricted WSL context. All twenty planned evaluator calls returned raw responses and were durably captured. There were no executor failures, retries, repairs, selections, or replacements.

Semantic conformance failed.

## Gate F findings

Gate F rejected all ten cases. It therefore produced no unsafe admissions, but falsely rejected all three fact-safe cases: 01, 02, and 04. Only Case 07 matched both the expected failure decision and decisive reason among the seven factual-semantic negatives. Cases 03, 05, 06, 08, 09, and 10 were rejected for the wrong semantic reason.

The dominant defect is overreach: the evaluator repeatedly treated explicitly figurative, conditional, personified, or editorial language as if it asserted factual emotion or intent. Examples include treating a hotel metaphor in the owner-quality positive Case 01 as unsupported emotion, treating a generic darkness metaphor in Case 02 as factual impact, and treating personification of the Danube in Case 04 as a factual claim about the river's mental state.

This violates the core architecture boundary: nonfactual commentary must remain permissible when it does not return to factual assertion. Conservative rejection alone is insufficient when the acceptance contract requires valid factual-to-comic transformation to pass.

For the seven true factual-semantic negatives, Gate F generally noticed that something was unsupported but failed to identify the governed proposition class:

- Case 03: motive instead of biography/history plus premise-to-directive.
- Case 05: emotion instead of institutional intent.
- Case 06: motive instead of history plus premise-to-directive.
- Case 08: emotion instead of outcome/status.
- Case 09: motive instead of work history plus physical capacity.
- Case 10: motive instead of certainty mutation, timing mutation, and life-stakes inflation.

## Gate S findings

Among the three cases with exact Gate S acceptance requirements:

- Case 01 correctly passed.
- Case 02 incorrectly passed despite being the frozen generic/portable negative.
- Case 04 was rejected, but as generic/portable rather than the required template-dominant class.

Gate S also labeled several factual-semantic negatives generic. Those diagnostic judgments do not cure Gate F failures and are not substitutes for the required factual-semantic proposition classes.

## Final decisions

Seven negative cases reached the expected final factual rejection, but six did so for nonconformant decisive reasons. Cases 01, 02, and 04 received false factual-semantic rejection. Case 01—the mandatory positive admission anchor—did not pass. Cases 02 and 04 never reached their correct owner-quality rejection precedence because Gate F rejected them first.

The frozen minimum conformance thresholds are not met. Semantic Admission V2 is not ready for runtime integration or activation.

## Authority boundary

All Run 4 outputs are quarantined evaluation evidence only. No current runtime behavior was affected. The run grants no curriculum, training, prompt, model, production, or runtime authority.

## Recommended next step

Perform a design-only Gate F failure analysis and bounded remediation specification. The primary requirement is to distinguish permitted nonfactual figurative transformation from unsupported factual propositions while preserving rejection of biography/history, intent, outcome/status, capacity, certainty/timing, and life-stakes mutations. Keep Gate S's Case 02 portability miss and Case 04 subtype miss as a separate remediation track. Do not patch prompts or execute another run until that specification is owner-reviewed.
