# Pastila News Monitor

A Python project for monitoring news sources related to Pastila.

The Scout polls configured RSS and HTML news sources, normalizes and stores new
articles, and places them in an editorial review queue.

## Source categories

Sources use one or more values from the controlled category vocabulary:
`Politica`, `Social`, `Conspiratii`, `Economie`, `CanCan`, `Externe`, and
`Diverse`. Categories describe a source's broad coverage, not individual
articles. Use the category filter to poll or validate only matching sources:

```powershell
pastila-scout poll-once --category Externe
pastila-scout validate-config --category Externe
```

Disabled sources are retained in `config/sources.yaml` when no dependable
public endpoint is available. `validate-config` reports them separately and
does not count them as failures.

## Editorial events

New articles remain independent database records and are also assigned to
locally matched editorial events. Matching uses recent normalized titles and a
conservative deterministic similarity threshold configured under
`event_matching` in `config/sources.yaml`; it does not call external or AI
services.

List recent events and their complete source provenance with:

```powershell
pastila-scout events --limit 20 --min-sources 2 --hours 168
```

## Requirements

- Python 3.14 or newer

## Development setup

Create and activate a virtual environment, then install the project with its
development dependencies:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Run the test suite with:

```powershell
pytest
```

## Scout → Editor public contracts

Milestone 6B provides frozen, versioned JSON contracts without implementing an
Editor Agent. The Editor boundary is file-based: it does not read Scout's
SQLite database, call an AI provider, or recalculate Scout scores.

The four public v1 contracts are:

- `scout-editor-input-v1`: official ranked Scout input;
- `editor-selection-profile-v1`: reusable selection constraints;
- `episode-context-v1`: episode-specific state and preferences;
- `editor-agent-output-v1`: validated proposal envelope for a future agent.

Validate a local contract, optionally checking an Editor output against its
exact Scout input:

```powershell
pastila-scout validate-contract contracts/samples/scout-editor-input-ai-v1.sample.json
pastila-scout validate-contract contracts/samples/editor-agent-output-success-v1.sample.json `
  --source-input contracts/samples/scout-editor-input-ai-v1.sample.json `
  --selection-profile contracts/samples/editor-selection-profile-v1.sample.json `
  --episode-context contracts/samples/episode-context-v1.sample.json
```

Validate and atomically rewrite canonical UTF-8 JSON, or regenerate the frozen
schemas and examples:

```powershell
pastila-scout export-contract INPUT.json --output OUTPUT.json
pastila-scout generate-contract-artifacts --output-directory contracts
```

`export-contract` accepts an existing public contract and performs validation
plus a canonical atomic rewrite. It does not construct or reinterpret Scout
ranking data.

Construct a new public `ScoutEditorInputV1` from an internal Scout ranking
report with the separate boundary adapter command:

```powershell
pastila-scout export-editor-input reports/event_ranking_TIMESTAMP.json `
  --output reports/scout-editor-input.json `
  --source-run-id snapshot:sha256:<64-lowercase-hex-characters> `
  --scout-version 0.1.0 `
  --ranking-schema-version event-ranking-v1 `
  --limit 100 `
  --top 10 `
  --minimum-score 55 `
  --ai-enabled
```

Use `--no-limit` instead of `--limit`, and `--no-ai` instead of
`--ai-enabled`, when those values describe the original ranking run. These
options are deliberately explicit because the internal report does not retain
enough information to infer them safely. The exporter preserves all Scout
scores and recommendations exactly and removes database paths, private IDs,
raw payloads, normalized titles, and provider/cache/usage diagnostics.

Representative provenance contains at most three articles. Selection first
maximizes distinct sources, then sorts by source priority descending, canonical
article preference, publication time descending, source ID, URL, and title.
The internal neutral priority default is one, undated articles follow dated
articles, and stable input order resolves otherwise identical records.

Committed JSON Schemas are in `contracts/schemas`; realistic documents are in
`contracts/samples`. Inputs reject unknown top-level fields, duplicate JSON
keys, incompatible versions, non-UTF-8 data, remote/UNC paths, oversized files,
and changed Scout fingerprints. Forward-compatible metadata is permitted only
inside explicit `extensions` objects.

Scout report identity uses canonical compact UTF-8 JSON with sorted object
keys, preserved array order, and no non-finite numbers. The identity projection
blanks `report_id` and `content_fingerprint`, hashes every other public
editorial field with SHA-256, and exposes both a tagged report ID and content
fingerprint. Optional diagnostic documents are outside this fingerprint.

## Deterministic editorial selection

`pastila_scout.editor.SelectionEngine` implements the Milestone 6C.1
contract-to-contract selection stage. It consumes only `ScoutEditorInputV1`,
`SelectionProfileV1`, and `EpisodeContextV1`, and returns an
`EditorAgentOutputV1` together with a private `DecisionTrace`.

Selection is composed from independent rules for mandatory and excluded
events, category balance, source diversity, freshness, Scout score preference,
runtime, backup quality, and editorial confidence. It determines membership,
then emits stable public-rank scaffolding for the separately executable flow
stage.

`pastila_scout.editor.EpisodeFlowOptimizer` consumes that selection result and
preserves the selected and backup sets exactly while optimizing order, segment
roles, transitions, pacing, treatment lengths, and total runtime. Its fixed
lexicographic objective is:

1. satisfy hard flow constraints;
2. preserve mandatory placement priority;
3. maximize opening strength;
4. maximize ending strength;
5. preserve early momentum;
6. improve category and tone rhythm;
7. handle score cliffs and previous-episode continuity;
8. favor inherited editorial strength;
9. break ties by public rank and event ID.

The optimizer uses a bounded beam with fixed width and no randomness. Supported
transitions are `continuation`, `contrast`, `escalation`, `hard_cut`,
`tone_shift`, `comic_relief`, and `callback`. `FlowDecisionTrace` retains the
initial and winning orders, summarized alternatives, objective components,
adjacency reasons, hard failures, and runtime allocation; it is private and
never enters the public report fingerprint.

Both stages use no provider, database, clock, randomness, or Scout internal
model. Required public text fields use fixed reason codes and templates. Current
non-goals are prose generation, semantic text analysis, AI reasoning, source
retrieval, and changing the selected or backup event sets.

## Deterministic editorial blueprint

`pastila_scout.editor.EditorialBlueprintBuilder` runs after flow optimization.
It returns the validated public output unchanged and creates a separate private
`EditorialBlueprint` plus `BlueprintDecisionTrace`. The blueprint describes
editorial function and narrative intent through controlled values; it does not
write episode language.

The private vocabulary covers:

- episode themes and tensions;
- segment intents and editorial angles;
- narrative functions;
- ordinal tension, energy, satire, and emotional levels;
- transition intents;
- controlled opening and closing functions;
- safe public fact fields and prohibited framing;
- explicit previous-episode continuity references.

For AI-scored public events, levels are derived only from existing 0–10 public
dimensions and clamped to 1–5:

- tension: `1 + floor((importance + public_interest) / 5)`;
- energy: `1 + floor((importance + virality + satirical_potential) / 8)`;
- satire: `1 + floor((absurdity + satirical_potential) / 5)`;
- emotional weight: `1 + floor((emotional_impact + public_interest) / 5)`.

Deterministic-only events use `1 + floor(final_score / 20)`, with satire one
level lower and all values clamped to 1–5. Category frequency uses the frozen
Romanian category order as its tie-breaker. No article text is classified or
semantically analyzed.

Evidence references must exactly match public Scout provenance. Safe fields are
limited to canonical title, canonical summary, publication bounds, categories,
and source provenance. The blueprint explicitly prohibits unsupported
causality, unverified motives, invented quotations, exaggerated certainty, and
source conflation.

The private trace records every assigned theme, intent, angle, ordinal curve,
transition intent, opening/closing decision, evidence reference, fallback, and
conflict. It is not part of the public contract or fingerprint. A future
AI-assisted language stage may consume this validated blueprint, but it must
remain subordinate to these evidence references and controlled decisions.
Current non-goals include scripts, hooks, jokes, titles, descriptions,
transitions, punchlines, or any other publishable prose.

## Project layout

```text
.
|-- src/
|   `-- pastila_scout/
|       |-- contracts/
|       `-- __init__.py
|-- contracts/
|   |-- samples/
|   `-- schemas/
|-- tests/
|-- AGENTS.md
|-- README.md
`-- pyproject.toml
```
