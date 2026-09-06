# Production Core Model Qualification Framework V1

Status: **Qualification Execution Profile v1 structural supervisor envelopes
owner-approved; inference and technical-output limits remain pending**.

Neither `experimental_core_v1_1` nor `experimental_core_v1_2` is production
authority. Version order has no evidentiary weight. Qualification may return
`NO_CANDIDATE_QUALIFIED`, and a PASS never promotes a candidate: promotion
requires a separate explicit owner designation.

## Frozen candidate-neutral gates

Every candidate receives the same immutable corpus, seeds, runtime budget,
manifest validator, and three clean-room repetitions. A candidate passes only
if every gate passes; there is no aggregate-score compensation.

| Category | Exact measurable PASS condition | Class |
|---|---|---|
| Semantic correctness | 100% of hard schema/constraint assertions and at least 95% of predeclared semantic case assertions pass in each of 3 runs | owner acceptance required |
| Factual preservation | 0 unsupported factual atoms, 0 changed protected atoms, and 100% required source-span bindings across all cases/runs | technical invariant |
| Core V2 contract | 100% schema, authority, ordering, identity, and fail-closed conformance assertions pass | technical invariant |
| Determinism | Byte-identical canonical output and receipts for all 3 repetitions of every deterministic case | technical invariant |
| Reproducibility | A second clean materialization reproduces 100% output identities | technical invariant |
| Failure isolation | Every injected malformed input/runtime/provider fault returns its declared terminal failure and causes 0 accepted-state mutations | technical invariant |
| Cancellation | 100% pre-start and checkpoint cancellations meet the candidate-free synthetically derived deadline, make 0 later provider calls, and publish 0 accepted output | deadline pending |
| Provenance/identity | 100% artifacts self-bind and transitively bind input, model, tokenizer, runtime, adapter, invocation contract, output, and qualification identities | technical invariant |
| Portability/runtime closure | Two clean offline materializations from the same manifest yield identical component hashes and pass all probes with no absolute host path | technical invariant |
| Resource ceilings | Every case remains inside separately frozen wall-time, peak-RSS, and technical bytes/tokens safety envelopes; these do not award semantic quality credit | values pending |
| Hidden fallback absence | 0 DNS/socket/HTTP calls, 0 model downloads, 0 undeclared file reads, and 0 alternate model/provider invocations under instrumented denial | technical invariant |
| Packaging viability | Clean offline install/materialization from declared artifacts succeeds twice and all production entry probes resolve only manifest-bound bytes | technical invariant |
| Migration compatibility | 100% V1.1, V1.2, missing/legacy, and fresh settings cases converge as specified below without inference or fallback | technical invariant |
| Comparative corpus performance | Each candidate independently satisfies every gate; pairwise comparison cannot rescue/disqualify a candidate and ties are legal | owner acceptance required |

The corpus contains exactly 200 unique case IDs in exclusive primary
partitions: 40 factual-authority/unsupported-claim, 30 qualification/uncertainty,
30 summarization/compression, 25 conflicting/insufficient-authority, 20
instruction-hierarchy, 20 completion/EOS/runaway, 20 Romanian editorial, and
15 malformed/boundary/adversarial cases. Secondary labels may overlap. At least
50 are true holdout cases excluded from training, tuning, prompt selection, and
threshold selection. Corpus and holdout identities are frozen before execution.

Owner has accepted the 95% semantic threshold, 3/3 determinism, 2/2 clean
reproducibility, 2/2 same-supported-platform portability, 2/2 offline packaging,
the corpus distribution, and all previously declared hard gates. For
Qualification Execution Profile v1 only, the owner also approved structural
supervisor envelopes of 500 ms cancellation, 1 s structural wall time, and
64 MiB structural peak RSS. These are not model-inference limits, global Core V2
policy, or global hardware requirements. Inference wall-time/RSS and technical
bytes/tokens limits remain unresolved. The semantic output ceiling is
independently derived from the Core V2 contract.

## Evidence

One canonical JSON qualification record binds: framework and corpus SHA-256;
candidate ID and bytes; tokenizer; runtime and ordered dependencies; provider
adapter; invocation contract; host-independent environment declaration; every
case input/expected/output/receipt identity; per-assertion results; timings and
resource measurements; injected-fault/cancellation traces; network and file
access denial logs; three-run determinism matrix; second-materialization
reproducibility matrix; aggregate gate decisions; and final result
`PASS`, `FAIL`, or `NO_CANDIDATE_QUALIFIED`. Raw outputs and logs are immutable
separate artifacts referenced by SHA-256. The record cannot contain a
production designation.

## Interim state and migration

`NO_PRODUCTION_CORE_DESIGNATED` is non-executable. Governed commentary and any
default Editor execution fail before provider/runtime resolution with that
exact actionable code. There is no fallback, path guessing, lookup, or download.

* Persisted V1.1 selection -> `NO_PRODUCTION_CORE_DESIGNATED` on load.
* Persisted V1.2 selection -> `NO_PRODUCTION_CORE_DESIGNATED` on load.
* Missing/legacy field -> `NO_PRODUCTION_CORE_DESIGNATED`.
* New installation -> `NO_PRODUCTION_CORE_DESIGNATED`.

Explicit experimental selections remain labelled experimental and outside
production authority; this framework does not execute them.

## Provider/runtime authority

Provider name is never model authority. Future production execution requires a
single owner-designated model ID plus SHA-256 identities for model, tokenizer,
runtime, provider adapter, and invocation contract. The portable manifest uses
logical names only, contains no machine path or secret, requires `DENY_ALL`
network policy, and is validated before any resolution. Resolution must occur
from an explicitly supplied content-addressed offline object store; missing or
mismatched objects fail closed.

No candidate result or score was inspected in creating these thresholds.

## Candidate-neutral execution-profile proposal

The owner-approved **Qualification Execution Profile v1** is WSL2 Linux x86-64
on Ubuntu 24.04, one NVIDIA accelerator with compute capability 12.0 and
16,303 MiB VRAM, 8 physical/16 visible logical CPU threads, and the observed
WSL memory and swap envelope. These values support only the first
candidate-neutral qualification. They are not global Core V2 minimum hardware
requirements and do not establish Core V2 portability policy. The inference
runtime must be rebuilt as a content-addressed offline rootfs; the mutable
installed WSL distribution is not authority.

Proposed inference settings are single-request/single-process execution,
one Torch intra-op and inter-op thread, disabled tokenizer parallelism, NF4
storage with BF16 compute and double quantization, greedy decoding
(`do_sample=false`, `temperature=0`, `top_p=1`), seed 0, deterministic kernels,
and fail-closed behavior when deterministic execution is unavailable. The owner
approved an 8192-token context for this qualification profile. No generated-token
limit is approved. In particular, 2000 tokens is not a semantic contract; any
future technical token limit is only a runtime safety envelope and awards no
semantic quality credit. None of these profile values promotes a candidate.

Candidate-free Windows and WSL structural probes converged on owner-approved
supervisor-only envelopes of 500 ms cancellation, 1 s structural wall time,
and 64 MiB structural peak RSS for Qualification Execution Profile v1. They do
not measure inference, are not per-case model ceilings, and do not define global
Core V2 policy or global hardware requirements.

The owner-approved factual output contract permits 2–3 propositions or 1–2
sentences, depending on the natural structure of the text, with a hard secondary
maximum of 650 Unicode characters. It is one text block with no bullets,
headings, trailing continuation, truncation, or continuation in another field.
Overflow is `FAIL`.

The owner-approved commentary contract permits at most 3 sentences and 1000
Unicode characters. It must permit a complete setup/observation, development,
and punchline when applicable. It is one text block with no trailing
continuation, truncation, or continuation in another field. Overflow is `FAIL`.

Semantic length is measured on canonical Unicode text after structural
validation. Contractual completion is terminal. Runtime/token budgets cannot
redefine or enlarge these limits.

The owner-approved Structured Qualification Response V1 is one JSON object with
exactly nine required ordered fields, no optional or additional fields, exact
request/case binding, the approved factual/commentary/abstention invariants, at
most 3 claim bindings, at most 8 source spans per claim and 24 aggregate.
Completion is the terminal `}` followed immediately by EOF. Every malformed,
additional, trailing, mismatched, truncated, or over-limit response fails as a
whole with no repair, coercion, extraction, retry, redraw, or state mutation.
Candidate output cannot contain or determine PASS/FAIL; only a separate
evaluator-authority receipt can record that verdict.

Technical token/byte and model-inference wall-time/RSS limits remain separate
and pending owner approval. The approved structural supervisor envelopes do not
resolve or imply them.

### Candidate-neutral technical-output envelope mechanism

Technical byte and token envelopes are derived only from a complete valid
Structured Qualification Response V1. The byte mechanism proves the maximum
canonical UTF-8 serialization length across every factual, commentary, and
abstention branch. The token mechanism applies the same frozen algorithm to the
exact content-addressed tokenizer declared by each candidate manifest, offline
and without loading model weights or inspecting candidate output. Different
tokenizer identities may produce different safety values; this has no scoring,
comparison, selection, or promotion effect.

No numeric envelope is yet authority. Derivation remains fail-closed until the
owner separately defines the exact JSON byte canonicalization, bounds the
currently unbounded `source_span_id`, and decides whether proven maxima are used
directly or receive a fixed non-semantic margin. Two clean derivations must bind
the serializer, contracts, runtime, tokenizer, implementation, results, and
negative regressions and must reproduce identical byte and token values.

This mechanism does not authorize candidate inference and cannot define or
infer model cancellation, wall-time, RSS, semantic quality, or global Core V2
policy.

## Unauthorized-default manifestation audit

The repaired production-authority manifestations were:

1. the packaged default settings selected V1.2;
2. missing/legacy settings migrated to V1.2;
3. persisted V1.1/V1.2 defaults survived loading as production selections;
4. the desktop selector silently fell back to an OpenAI/Ollama model;
5. integrated governed commentary required V1.2 by name;
6. ordinary default Editor execution could consume the experimental default;
7. the production Voice composition constructed the V1.2 executor directly;
8. unavailable governed Voice execution reported only a generic local-model
   failure, and one receipt fallback attributed V1.2 without a receipt.

Experimental modules, adapters, tests, and historical evidence that explicitly
identify V1.1 or V1.2 remain experimental evidence, not defaults or production
authority. They were neither deleted nor reclassified, and no candidate was
executed. Scout provider settings are separate from Production Core authority
and were not reinterpreted.
