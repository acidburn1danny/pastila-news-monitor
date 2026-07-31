# Reference Examples

## Observation and evidence

Correction `import-1` references `graph-1`; operation `remove_connector` references intent `increase_conversational_naturalness`; `obs-1` references all three plus episode/story/editor provenance. Appending `obs-2` creates a new evidence chain retaining the old chronology as an exact prefix.

## Candidate and lifecycle

Aggregation of `obs-1`, `obs-2`, and `obs-3` may create inactive `candidate-1`. Threshold and review may move it candidate → emerging → established; rejection moves it to rejected. Explicit `rule-1` follows explicit_editor_rule → established. Candidates never influence guidance directly.

## Conflict, decay, profile, and guidance

Opposite `obs-4` remains in counter-evidence. `conflict-1` links predecessor, successor, evidence, explanation, and confidence impact; supersession retains both IDs. Aging produces a new decay artifact while explicit rules do not auto-decay. New profile snapshots keep deprecated, archived, rejected, and superseded knowledge visible. Guidance exposes accepted IDs and metadata but no generated sentence, joke, transition, or script.
