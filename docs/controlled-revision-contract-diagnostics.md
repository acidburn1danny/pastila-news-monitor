# Controlled Revision Contract Diagnostics

## Scope and evidence

Part 7D analyzed the single Part 7C baseline artifact and its single immutable
history entry. It made no provider, SDK, or network requests and did not replay
any scenario. All 24 scenario IDs and all 12 categories were analyzed in their
original order. The frozen schema fingerprint remains
`70f4ad299e9c35e86ab473705ed449a244ead2e9574745012cc179afbf6a9556`.

The retained artifact contains diagnostic codes but not provider-produced
reference values. Consequently, exact unknown and unauthorized references,
the first invalid value, overlap, precision, recall, frequency, and confusion
pairs cannot be recovered. The JSON artifact represents those measurements as
`null`; it does not infer or invent them.

## Failure localization

| Failure | Count | First deterministic stage | Validator |
|---|---:|---|---|
| `openai_provider_output_reference_unknown` | 12 | authorization mapping | deterministic reconstructor |
| `openai_provider_output_reference_unauthorized` | 11 | authorization mapping | deterministic reconstructor |
| `openai_provider_output_schema_invalid` | 1 | provider DTO validation | Pydantic provider-output DTO |

The 23 reference failures passed provider response parsing and DTO validation
before the reconstructor compared the returned reference set with the exact
authorized set. The schema failure stopped earlier. Every benchmark scenario
has a localized record in the JSON artifact.

## Reference contract analysis

Every frozen benchmark invocation authorizes exactly `story:101`. Projection
was reconstructed offline for every scenario and retained invocation identity
and fingerprint equality.

The runtime contract is exact: returned references must equal the invocation's
authorized references. The provider-visible story schema instead accepts any
positive story identifier matching `^story:[1-9][0-9]*$`. It validates the
reference's syntax and component type, but it does not constrain the value to
the invocation-specific authorized set. Thus a reference can be schema-valid
and still be rejected deterministically as unknown or unauthorized.

The reference contract is therefore incomplete at the provider-schema
boundary, under-specified with respect to invocation-specific values, and
ambiguous across the combined prompt/schema interface. It is not internally
inconsistent: the schema and runtime operate at different levels of strength.
There is no evidence that runtime authorization is over-constrained.

## Prompt analysis

The frozen prompt clearly requires one result for every supplied editable
reference, exact copying of each reference, and no unauthorized reference. The
projected input separately carries required references and editable component
references. No conflicting reference instruction or implicit reference rule
was found.

The prompt is therefore not demonstrated to be ambiguous. Because actual
provider-produced reference values were not retained, the evidence cannot
distinguish whether the provider ignored this explicit instruction or whether
the generic strict schema exerted stronger generation guidance.

## Schema analysis

The provider schema strictly constrains object properties, component shapes,
and reference syntax. It does not encode the exact authorized values for the
current invocation. This permits invalid-but-schema-compliant story IDs and
other valid component branches. The dynamic-reference gap is detectable
offline by comparing the projected authorized set with the schema's accepted
reference language.

This is strong evidence for a schema-boundary risk, but it is not proof that a
specific generated reference caused the 23 failures because those values are
absent from the retained evidence.

## Authorization analysis

`OpenAIControlledRevisionReconstructor.reconstruct` computes the expected and
returned reference sets, rejects returned references outside the expected set,
distinguishes known-but-unauthorized references from unknown references, and
rejects missing required references. Its behavior is deterministic and agrees
with the documented exact-set contract. No retained evidence shows a valid
authorized reference being rejected incorrectly.

## Benchmark runner analysis

Offline reconstruction confirms request projection was valid for all 24
scenarios. The provider responses were captured sufficiently for production
interpretation, and reference extraction ran because the reconstructor emitted
specific unknown/unauthorized diagnostics.

The Part 7C diagnostic artifact has two confirmed runner defects:

1. It did not retain a bounded, content-safe list or hash of produced reference
   identifiers. Required per-reference diagnostics are therefore impossible.
2. It recorded 23 deterministic provider-output reference rejections as
   `PROVIDER_FAILURE`. Their correct bounded operational class is
   `PROVIDER_OUTPUT_REJECTED_SAFELY`.

Provider request counts, retry counts, fallback counts, scenario IDs,
categories, and diagnostic-code counts are accurate. Token, latency, and cost
data were unavailable after failed interpretation and must not be interpreted
as measured zero usage.

## Failure clusters and categories

The evidence contains two clusters: 23 reference-contract rejections and one
provider DTO schema rejection. Reference failures affect every category; the
single DTO failure is `SYN-07`, in `PROTECTED_STRUCTURE`. The full deterministic
category distribution is stored in the JSON artifact.

No exact reference frequency table or confusion matrix can be produced from
the retained data. The most common *failure class* is unknown reference (12),
but the most common unknown *reference value* is unavailable. Likewise, the
most common unauthorized reference value is unavailable.

## Offline detectability

- The schema's lack of invocation-specific reference constraints was
  detectable during an offline provider-schema construction audit.
- A particular returned-reference mismatch is detectable only after receiving
  and DTO-validating the provider response, at authorization mapping.
- The runner's missing diagnostic fields were detectable offline by validating
  the artifact contract against Part 7D's required diagnostics. Such a
  preflight could have prevented all 24 requests from being used by a runner
  unable to retain the evidence required for root-cause attribution.
- The request reduction attributable specifically to the schema gap cannot be
  quantified without the missing produced references.

## Candidate root causes

### Generic provider schema — HIGH confidence

Evidence: the schema accepts non-authorized values by pattern, while 23
DTO-valid responses failed exact-set authorization. Alternative explanation:
the provider ignored explicit reference-copy instructions. Attribution between
these alternatives is not possible from retained evidence.

### Provider reference non-compliance — MEDIUM confidence

Evidence: 23 responses did not satisfy the exact authorized set. Alternative
explanation: the generic strict schema guided generation toward a different
schema-valid branch or identifier. Actual values are unavailable.

### Runner diagnostic/classification defect — HIGH confidence, confirmed

Evidence: reference values are absent and 23 mapping failures were classified
as generic provider failures. This defect prevents attribution but did not
cause the original provider output mismatch.

## Conclusion

The evidence proves a runner diagnostic and classification defect and exposes
a material schema-boundary risk. It cannot prove whether the failed reference
values were primarily caused by schema guidance or provider non-compliance.
The evidence-based root conclusion is therefore `INSUFFICIENT_EVIDENCE`.

The immediate recommendation is `FIX_RUNNER_ONLY`: restore adequate bounded
diagnostic capture and correct operational classification before authorizing
another baseline. This recommendation does not propose or authorize production
prompt, schema, DTO, authorization, runtime, or provider changes.
