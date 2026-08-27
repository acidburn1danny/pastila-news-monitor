# Semantic Admission V2 — Gate F failure analysis and bounded remediation design

## Conclusion

Run 4 exposed a semantic-boundary failure, not a decoding or infrastructure failure. Gate F produced valid governed JSON on every call, but it judged rhetorical surfaces instead of unsupported real-world propositions. It treated metaphor, personification, emotional color, and editorial stance as factual commitments, while assigning broad emotion/intent labels to materially different unsupported claims.

The narrow remediation is proposition-and-scope discipline inside the evaluation-only Gate F contract. It must not weaken factual authority, create a metaphor allowlist, route by cue words, alter Voice/Core generation, or touch Gate S.

## Required distinction

Gate F must ask whether the commentary commits the reader to an unsupported proposition about the real story. It must not ask whether the line contains imaginative language.

Metaphor, analogy, personification, marked counterfactuals, hyperbole, wordplay, and editorial evaluation remain permitted nonfactual transformations when they stay inside their creative scope. They fail only when they assert, presuppose, entail, or return to an unsupported real-world proposition.

Gate F must evaluate every real-world proposition carried by the commentary, including propositions introduced through presupposition, entailment, or necessary implication. A figurative or editorial surface semantic head cannot shield a different unsupported proposition embedded or presupposed inside the construction.

This distinction allows Cases 01, 02, and 04 to pass without weakening rejection of Cases 03 and 05–10.

## Run 4 diagnosis

- Case 01: a hotel/room/transparency metaphor was incorrectly converted into hotel emotion or need.
- Case 02: generic darkness imagery was incorrectly treated as factual emotional impact. Genericity belongs to Gate S.
- Case 04: explicit river personification was literalized into river thought, intent, and emotion. Template quality belongs to Gate S.
- Cases 03, 05, 06, 08, 09, and 10 were rejected, but their decisive proposition classes were replaced by nearby rhetorical emotion or intent.
- Case 07 was the only negative with the expected decisive Gate F class.

The remediation specification therefore requires an ordered proposition inventory, speech-act/scope test, fiction-return test, authority comparison, and semantic-head classification before a decision.

## Bounded path

The preferred first implementation, if separately authorized, is a versioned change only to the evaluation-only Gate F semantic contract. The constrained JSON grammar, reason-code namespace, model, factual authority, precedence, and Gate S remain unchanged.

Before a full rerun, the candidate should pass zero-inference identity and trie checks, then a two-case Gate F-only probe covering the mandatory positive and a hard figurative-to-factual-return negative. A later ten-case Gate F run must achieve zero false factual rejections, zero unsafe passes, zero wrong decisive reasons, and zero evaluator failures.

If prompt-only remediation cannot satisfy the probe, stop and report a capability limit. Do not compensate with lexical heuristics, automatic metaphor passes, reason relabeling, retries, or output repair.

## Separate Gate S track

Gate S remains outside this design. Its Case 02 generic-portability false pass and Case 04 template-versus-generic subtype error are preserved as independent defects. No Gate S artifact or behavior is authorized to change here.

## Authority

Design only. No implementation, prompt/model modification, inference, runtime integration, curriculum exposure, enrichment, or training is authorized.
