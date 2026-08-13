"""Run the compact Scout tuning dataset through explicit local Ollama."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.scout_prompt_tuning_v1 import (
    execute_ollama_prompt,
    load_tuning_dataset,
    run_tuning,
    save_tuning_result,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scout prompt tuning — Ollama first")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--provider", choices=("ollama",), default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--variant", default="current")
    parser.add_argument("--prompt-override", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    override = (
        None
        if arguments.prompt_override is None
        else arguments.prompt_override.read_text(encoding="utf-8")
    )
    dataset = load_tuning_dataset(arguments.dataset)
    try:
        result = run_tuning(
            dataset=dataset,
            model=arguments.model,
            base_url=arguments.base_url,
            timeout=arguments.timeout,
            execute=lambda prompt: execute_ollama_prompt(
                prompt,
                model=arguments.model,
                base_url=arguments.base_url,
                timeout=arguments.timeout,
            ),
            variant=arguments.variant,
            override=override,
        )
    except Exception as exc:  # noqa: BLE001 - CLI presents local provider failures
        print(f"Provider: Ollama\nModel: {arguments.model}\nEroare: {exc}")
        return 2
    output = arguments.output or Path("reports/scout-prompt-tuning") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".json"
    )
    save_tuning_result(output, result)
    metrics = result["metrics"]
    print(f"Provider: Ollama\nModel: {arguments.model}\nCases: {metrics['cases']}")
    for label, key in (
        ("Relevance", "relevance"),
        ("Category", "category"),
        ("Duplicate handling", "duplicate"),
        ("Priority agreement", "priority"),
    ):
        score = metrics[key]
        print(f"{label}: {score['correct']}/{score['total']}")
    print(f"False positives: {len(metrics['false_positives'])}")
    print(f"False negatives: {len(metrics['false_negatives'])}")
    for mismatch in metrics["mismatches"]:
        print(f"Mismatch {mismatch['id']}: {', '.join(mismatch['fields'])}")
    print(f"Result: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
