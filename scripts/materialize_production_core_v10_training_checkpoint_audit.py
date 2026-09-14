"""Materialize the content-addressed V10 training checkpoint/resume audit receipt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v10-training-checkpoint-resume-audit.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def build_receipt() -> dict[str, object]:
    core = {
        "schema": "pastila-production-core-v10-training-checkpoint-resume-audit",
        "schema_version": 1,
        "status": "PASS_ZERO_BLOCKERS_CHECKPOINT_SAVE_RESTART_RESUME_BYTE_EXACT",
        "source_commit": "fe46c5ef9806a83c14cb4a4598525eedb044c4ec",
        "source_tree": "9f47ea9e08979bdecc4294a2411bd01f79bdef94",
        "launcher_sha256": "69381e707890b052bebe98fd481f29cf318351f8ba8694cc512d9a502763170f",
        "trainer_sha256": "aaafcf3794e335e6757b9ee23a1cc21b5e9e6bc6e33cf055de0e2c2963252669",
        "rootfs_sha256": "9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826",
        "optimizer": "PAGED_ADAMW_8BIT",
        "smoke": {
            "resumed_receipt_identity": "f7d28e3e229fd5bd9cd09060fa83fc6ea70bf0d6da4e3bacf7a2771377841756",
            "resumed_receipt_sha256": "c6a8bbeadafdbcf0f761428e153ee887a8f4b424355716dbd9eeaad6dc52f229",
            "control_receipt_identity": "43f80f9f2627dd7871865231e7c8c74e1a8d0eb4fc283983b6f6b408938e123f",
            "control_receipt_sha256": "0b2aff2c714b7159009ca5101d56f3a0767a03d6cb58b879d95a5ca30130af29",
            "checkpoint_identity": "9a2be217926c0ede64b5ec44c02c7fd678a1a122c4123ff38e09dc262160d0de",
            "checkpoint_manifest_sha256": "c798b7b889a344c608236ef8fe677683553a79538e042c630b381b08610d397a",
            "checkpoint_state_sha256": "207f00e690107d1df754556186baade56c854293787c4d41b6b1437ab71f55d1",
            "progress_sha256": "640b13f0fcf665641bb40c1ccc2ea0673f955ad7034adcd0c85666c88019e5cf",
            "final_adapter_sha256": "5edf5db9b1e31e659ed1ac14aa45e472379291d36bc0e73b470d5a5eec43924f",
            "optimizer_steps": 1,
            "recalculated_accepted_microsteps": 0,
            "adapter_closure_byte_exact": True,
            "save_reload": True,
            "triton_compile_load": True,
            "backward_4bit": True,
        },
        "negative_regressions": {
            "wrong_authority_binding": "REJECTED",
            "tampered_adapter": "REJECTED",
            "tampered_progress": "REJECTED",
            "missing_checkpoint_state": "REJECTED",
            "symlink_checkpoint_root": "REJECTED",
            "orphan_after_sigterm": False,
            "gpu_leak_after_sigterm": False,
        },
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "audit_identity": hashlib.sha256(canonical(core)).hexdigest()}


def main() -> int:
    value = build_receipt()
    raw = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    if OUTPUT.exists() and OUTPUT.read_bytes() != raw:
        raise SystemExit("published checkpoint audit differs")
    if not OUTPUT.exists():
        OUTPUT.write_bytes(raw)
    print(value["audit_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
