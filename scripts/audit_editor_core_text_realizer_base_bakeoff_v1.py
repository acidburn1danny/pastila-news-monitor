"""Adversarial design audit for the fixture-only base bake-off."""
from __future__ import annotations

import json
from fixture_editor_core_text_realizer_base_bakeoff_v1 import run


def main() -> None:
    result = run()
    checks = [
        result["status"] == "PASS_FIXTURE_ONLY", result["arms"] == 3, result["cases"] == 48,
        result["source_bindings"] == 4,
        result["valid_acceptances"] == 144, result["adversarial_fallbacks"] == 144,
        not result["models_downloaded"], not result["model_loaded"], not result["inference_performed"],
        not result["optimizer_created"], not result["training_performed"], not result["historical_holdouts_read"],
    ]
    if not all(checks):
        raise ValueError("adversarial closure failed")
    print(json.dumps({"status": "PASS_ADVERSARIAL", "checks": len(checks), "pack_identity": result["pack_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
