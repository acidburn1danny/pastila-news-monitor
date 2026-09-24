# Editorial Mechanics Bridge structural inference successor v3.1

## Decision

V3.1 is a bounded execution-route repair of v3. The published v3 route passed the structural fixtures but failed before chroot because Bash parsed `$14` as `${1}4`. V3.1 uses the braced positional expansion `${14}` for the structural-constraint source passed to the child mount namespace.

The worker, JSON DFA/tokenizer constraint, tokenizer preflight, response audit and supervisor remain byte-identical to v3. Model, adapters, requests, candidate order, limits, qualification semantics, failure evidence and the 168/168 closure requirement are unchanged.

An executable regression test exercises Bash positional arguments 10 through 14 and binds the route source to the braced argument-14 mount expression. It fails if the unbraced `$14` form returns.

## Historical state

The v3 execution failure journal and empty output directories remain immutable historical failure evidence. V1, v2 and v3 outputs are ineligible for scoring. A v3.1 execution must use new empty roots and cannot prepare packets until all seven candidates pass the published structural audit.
