# Controlled Revision duplicate-reference generation investigation

## Executive summary

Part 5M made zero live and SDK requests and changed no production behavior. The
deterministic E2E-02 invocation contains one unique authorized reference and one
projected component. Projection preserves identity, cardinality, uniqueness, and
order. The prompt presents the same value in two consistent data sections and
explicitly requires one output, exact copying, no omission, and no unauthorized or
duplicate reference.

The SDK returns the raw response object. The interpreter extracts one text block,
decodes it once with `json.loads`, and passes that object directly to the DTO. No
local layer concatenates, duplicates, normalizes, or rewrites components before
validation.

Root conclusion: `PROVIDER_DUPLICATE_GENERATION_CONFIRMED`.

Recommendation: `KEEP_CURRENT_PRODUCTION_BEHAVIOR`.

## Part 5K live failure and Part 5L ownership

The Part 5K replay eliminated the historical reference/type mismatch but produced
one root-level `duplicate_component_reference` error, with no union noise. Part 5L
confirmed that property-level cross-item uniqueness belongs in the DTO and cannot
be replaced by generic `uniqueItems`.

## Frozen boundaries

The prompt, component-shape block, corrected schema and fingerprint, DTO and
validators, projection, SDK adapter, interpreter, reconstructor, runtime, retries,
fallbacks, gateway, and model selection were not modified.

## E2E-02 invocation reconstruction

The deterministic fixture contains six source-level components but authorizes and
projects exactly one target component for revision. The authorized reference count,
unique-reference count, projected component count, and projected unique-reference
count are all one. Source and projected ordering are deterministic. Classification:
`FIXTURE_VALID` and `INPUT_REFERENCES_UNIQUE`.

## Reference lineage

Safe alias R01 maps one-to-one through source targeting, projection, provider input,
the schema field, DTO field, interpreter pass-through, and reconstructor lookup. No
layer duplicates, rewrites, normalizes, sorts, drops, merges, aliases, or reindexes
the reference.

## Prompt occurrence and instruction audit

R01 occurs twice in the provider input: once in the authorized-reference list and
once as the corresponding editable component field. It does not occur as a value in
the instruction block or schema. Classification:
`MULTIPLE_REFERENCE_OCCURRENCES_BUT_UNAMBIGUOUS`.

The actual instruction block explicitly states:

- one output per authorized input;
- exact reference copying;
- each authorized reference appears exactly once;
- no missing or unauthorized references;
- source type preservation;
- complete, non-hybrid variant shapes;
- a final structural self-check.

Order preservation is not stated explicitly. With one projected component, that
omission cannot explain this occurrence and creates no mapping ambiguity.

## Fixture integrity

Source story identities, transition identities, projected target identities, and
the single commentary-block position are deterministic and nonduplicated. One
source identity produces one projected component. Classification: `FIXTURE_VALID`.

## DTO validator audit

The root validator compares the parsed `component_reference` strings directly and
deterministically. It applies no case folding, Unicode normalization, separator
normalization, prefix rewriting, aliasing, or index coercion.

Local results:

- identical reference and body: one duplicate root error;
- identical reference with different body: one duplicate root error;
- identical body with different valid references: accepted;
- case, Unicode-separator, separator, and prefix variants: never falsely classified
  as duplicates (invalid formats fail their own field rules);
- different valid indexes and different component types: remain distinct.

The retained live topology is consistent with a genuine exact string duplicate and
not with a DTO false positive.

## Schema/DTO differential

Two nonidentical components sharing one reference pass the corrected schema and fail
the DTO. Two identical components behave the same under the production schema. A
synthetic `uniqueItems` schema would reject only the identical-object case, not the
different-body case. This confirms the Part 5L ownership boundary.

## Post-provider and SDK mutation audits

`OpenAIProviderClient.send` returns the raw SDK response as its payload. A mocked
transport verifies object identity is preserved. The interpreter requires one
completed output message containing one output-text block, performs one JSON decode,
and passes the decoded object directly into `model_validate`. It performs no array
copy, merge, append, extension, sorting, or reconstruction before DTO validation.

Classifications: `SDK_TRANSFORMATION_EXCLUDED` and
`LOCAL_POST_PROVIDER_MUTATION_EXCLUDED`.

## Safe failure topology and sufficiency

The existing evidence proves at least one exact reference appeared at least twice
in the decoded provider-originated object. It does not preserve the duplicate
position, type relationship, body relationship, omitted reference, duplicate-group
count, or multiplicity beyond two.

Existing diagnostics are `PARTIALLY_SUFFICIENT`: enough to confirm genuine provider
duplication after excluding local layers, but not enough to distinguish the detailed
generation mechanism. Aggregate component/unique counts, duplicate-group count,
maximum multiplicity, type histogram, and coarse positional distance would be
`USEFUL_BUT_NOT_REQUIRED`. No production diagnostic change is made.

## Generation-risk factors and perturbations

The projected set contains one component, one type, no transitions, no similar
prefixes, no adjacent components, one commentary block, and no large output shape.
One-to-one rules are repeated, but there is no evidence that repetition caused the
failure. Prompt density remains unknown and merely plausible. Deterministic local
perturbations confirm that counts, prefix similarity, ordering, and repetition alter
presentation metrics, but cannot establish model causation.

## Hypothesis matrix

| Hypothesis | Outcome |
|---|---|
| H1 input duplicated | FALSIFIED |
| H2 projection duplicated | FALSIFIED |
| H3 one reference mapped to multiple inputs | FALSIFIED |
| H4 schema generated duplicate slots | FALSIFIED |
| H5 DTO false positive | FALSIFIED |
| H6 SDK duplicated | NOT_SUPPORTED |
| H7 local JSON handling duplicated | FALSIFIED |
| H8 interpreter duplicated | FALSIFIED |
| H9 provider generated duplicate | SUPPORTED |
| H10 ambiguous mapping encouraged duplicate | NOT_SUPPORTED |
| H11 stochastic noncompliance | PARTIALLY_SUPPORTED |
| H12 diagnostics cannot distinguish H10/H11 mechanism | SUPPORTED |

## Evidentiary limits and provider attribution

The decoded object necessarily contained duplicate equal reference strings because
the deterministic DTO validator triggered. All transformations from the raw SDK
response to DTO input preserve the single output text and decoded array. Therefore
provider duplicate generation is confirmed at the provider-originated structured
object boundary. The evidence does not prove why the model generated it or whether
the behavior is stochastic.

## Privacy

The artifact contains safe aliases, counts, booleans, classifications, fingerprints,
and synthetic aggregate topology only. It retains no real or hashed references,
source/provider prose, prompt body, output, raw DTO input, request identifiers,
credentials, exceptions, or stack traces.

## Findings

- **P5M-INPUT / informational / HIGH:** input and fixture references are unique.
  Impact: input duplication excluded; follow-up: none; architecture impact: none.
- **P5M-PROJECTION / informational / HIGH:** projection preserves one-to-one
  cardinality and order. Impact: projection defect excluded.
- **P5M-PROMPT / informational / HIGH:** mapping rules are explicit and
  noncontradictory; two legitimate occurrences are unambiguous.
- **P5M-DTO / informational / HIGH:** validator correctly identifies exact string
  duplicates with one root error and no union noise.
- **P5M-SDK / informational / HIGH:** raw response identity is preserved; SDK-side
  component transformation is excluded by adapter behavior and mocked tests.
- **P5M-PIPELINE / informational / HIGH:** one JSON decode feeds the DTO directly;
  local duplication is excluded.
- **P5M-PROVIDER / high / HIGH:** the provider-originated decoded object contained a
  duplicate reference. Detailed generation mechanism remains unknown.
- **P5M-DIAGNOSTICS / low / MEDIUM:** more aggregate topology would aid recurrence
  comparison but is not required to keep failing closed.
- **P5M-ARCHITECTURE / informational / HIGH:** current DTO ownership remains correct.

## Root conclusion

`PROVIDER_DUPLICATE_GENERATION_CONFIRMED`

## Final recommendation

`KEEP_CURRENT_PRODUCTION_BEHAVIOR`
