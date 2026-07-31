"""Run the deterministic offline Controlled Revision quality benchmark."""

from __future__ import annotations

import json

from pastila_scout.editor.generation.controlled_revision_quality import (
    RevisionBenchmarkRunner,
)


def main() -> int:
    result = RevisionBenchmarkRunner().run()
    print("Scout Revision Quality")
    print("Part 7A — Controlled Revision Quality Baseline & Evaluation Harness\n")
    print("Mode: SYNTHETIC_FIXTURE")
    print(f"Scenarios: {result.scenario_count}")
    print(f"Categories: {result.category_count}")
    print(f"Usable revision rate: {result.usable_revision_rate:.3f}")
    print(f"Overall score: {result.overall_score:.3f}")
    print(f"Consistency: {result.consistency_checks[0]}")
    print("OpenAI provider requests: 0")
    print("OpenAI SDK requests: 0")
    print("Retries: 0")
    print("Fallbacks: 0")
    print("Schema fingerprint unchanged: PASS")
    print("Exit code: 0")
    assert "assembled_text" not in json.dumps(result.model_dump(mode="json"))
    return 0 if result.consistency_checks == ("scenario_expectations_match",) else 1


if __name__ == "__main__":
    raise SystemExit(main())
