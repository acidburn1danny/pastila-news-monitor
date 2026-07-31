# Editorial Knowledge Base

The initial knowledge base contains seven findings extracted from Part 7H, Part 7H.2,
the canonical experiment manifest, and the Part 7H.2.2 trade-off analysis.

Key established knowledge:

- quote-specific preservation reduced observed `QUOTE_MUTATION` from two cases to zero;
- the narrow gain did not make H2 production-suitable and net editorial utility was -2;
- removing quote failure exposed pre-existing source-authority failure in two cases;
- editorial acceptance needs criterion-level explanation;
- Net Editorial Utility supplements but never replaces editorial acceptance;
- a single-mechanism Prompt Delta Budget bounds causal interpretation;
- canonical manifests make experiment conclusions reproducible.

The suggested “prompt rigidity” finding was deliberately excluded because the frozen
taxonomy and paired diagnostics do not isolate or name that failure.

The machine-readable base is `docs/artifacts/editorial-knowledge-base.json`. The
companion `docs/artifacts/editorial-knowledge-index.json` indexes IDs by category,
confidence, finding type, experiment, and scenario for future query work; it does not
implement search.

Future workflow:

1. Complete and validate an experiment manifest.
2. Produce scenario-level causal/trade-off analysis.
3. Extract only evidence-supported, reusable findings.
4. Deduplicate and validate evidence, relationships, scenarios, and fingerprints.
5. Append or version knowledge without destroying historical findings.
6. Use active knowledge as evidence for future prompt design, not as an automatic
   prompt decision engine.

This milestone remains offline and does not alter prompts, provider behavior, rubric,
reference projection, or experiment results.
