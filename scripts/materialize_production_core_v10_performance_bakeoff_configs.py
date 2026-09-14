"""Materialize fail-closed V10 BATCH_SMOKE performance variants."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
VARIANTS = (
    "BASELINE",
    "FLASH_ONLY",
    "EFFICIENT_ONLY",
    "EXPANDABLE_ALLOCATOR",
    "FLASH_ONLY_EXPANDABLE_ALLOCATOR",
    "FLASH_REPEAT_KV",
    "FLASH_REPEAT_KV_EXPANDABLE_ALLOCATOR",
    "BF16_AUTOCAST",
    "BF16_AUTOCAST_FLASH_REPEAT_KV",
    "BF16_AUTOCAST_FLASH_REPEAT_KV_EXPANDABLE_ALLOCATOR",
    "BF16_FLASH_REPEAT_KV_MEMORY_DIAGNOSTIC",
    "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS_DIAGNOSTIC",
    "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS",
    "BF16_FLEX_ATTENTION_SELECTIVE_LOGITS_DIAGNOSTIC",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def materialize(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    source = ART / "pastila-editor-core-v1.1-json-successor-v10-training-config-v10.json"
    frozen = json.loads(source.read_bytes())
    frozen.pop("training_config_identity")
    artifacts: dict[str, object] = {}
    for variant in VARIANTS:
        core = {
            **frozen,
            "performance_variant": variant,
            "performance_bakeoff_only": True,
            "full_training_authorized": False,
        }
        if variant in {
            "BF16_FLASH_REPEAT_KV_MEMORY_DIAGNOSTIC",
            "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS_DIAGNOSTIC",
            "BF16_FLEX_ATTENTION_SELECTIVE_LOGITS_DIAGNOSTIC",
        }:
            core["performance_probe_microsteps"] = 1
        value = {**core, "training_config_identity": hashlib.sha256(canonical(core)).hexdigest()}
        raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
        path = output / f"v1.1-{variant.lower().replace('_', '-')}.json"
        path.write_bytes(raw)
        artifacts[variant] = {
            "path": path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "training_config_identity": value["training_config_identity"],
        }
    manifest_core = {
        "schema": "pastila-production-core-v10-performance-bakeoff-config-manifest",
        "schema_version": 1,
        "status": "BATCH_SMOKE_ONLY_ZERO_FULL_TRAINING",
        "source_config_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "batch_rows": 8,
        "hard_gate_speedup": 3,
        "target_speedup": 4,
        "stretch_speedup": 5,
        "variants": artifacts,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
    }
    manifest = {**manifest_core, "manifest_identity": hashlib.sha256(canonical(manifest_core)).hexdigest()}
    (output / "manifest.json").write_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(materialize(args.output_dir)["manifest_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
