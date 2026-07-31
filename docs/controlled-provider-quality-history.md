# Controlled Provider Quality History

## Purpose

`docs/artifacts/controlled-provider-quality-history.json` is the append-only,
versioned record of completed provider quality benchmarks. Part 7B.1 creates an
empty schema because it performs no benchmark execution.

The history supports longitudinal comparison of quality, editorial acceptance,
DTO validity, meaning preservation, latency, token use, cost, providers, models,
prompts, schemas, and pricing versions.

## Schema

The root contains `schema_version` and `history`. Version 1 entries contain the
complete identity, configuration lineage, quality rates, latency aggregates,
token aggregates, cost aggregates, request counts, and terminal conclusion
required by Part 7B.1.

Models are immutable and accept unknown fields so older readers can preserve
future additive metadata. Required v1 fields remain strictly validated.

## Benchmark identity

IDs use `YYYYMMDD-HHMMSS-provider-model`, for example
`20260728-143015-openai-gpt-4.1-mini`. IDs must be unique. Dates are timezone-aware
ISO 8601 values and entries are ordered by benchmark date.

## Append-only integrity

Appending validates the existing artifact first, rejects duplicate IDs and
out-of-order dates, canonicalizes every historical entry before and after the
append, and refuses the write if any previous entry changes. The resulting JSON
is written to a sibling temporary file, flushed, synchronized, and atomically
replaced. Corrections therefore require a new benchmark entry.

The physical JSON document is atomically replaced because portable JSON files
cannot be extended safely in place; the semantic history is strictly append-only.

## Compatibility

`schema_version` is explicit. Additive unknown fields are retained by the models,
allowing future schema evolution while preserving older entries. A future
breaking schema requires a new root version and an explicit reader migration.

## Usage

Call `create_benchmark_history(path)` to initialize or validate an artifact,
`load_benchmark_history(path)` to read it, and
`append_benchmark_history(path, entry)` only after a benchmark has completed.

Part 7B.1 does not append a synthetic or placeholder run.

## Validation

Tests cover empty creation, repeated creation, append, immutable-prefix
preservation, duplicate rejection, out-of-order rejection, schema validation,
unknown-field compatibility, atomic UTF-8 persistence, and frozen models.

## Root conclusion

`BENCHMARK_HISTORY_READY`

## Final recommendation

`READY_FOR_PROVIDER_BASELINE`
