"""Materialize the audited V5 adapter receipt and zero-qualification candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sealed(core: dict, field: str) -> dict:
    return {**core, field: identity(core)}


def audit_receipt() -> dict[str, object]:
    core = {
        "schema": "pastila-production-core-v1.1-successor-adapter-audit-receipt",
        "schema_version": 5,
        "status": "PASS_ZERO_QUALIFICATION_ATTEMPTS",
        "branch": "successor/core-v2-v1-1-eos-remediation-v5",
        "training_source_commit": "a140a612a7c80131064d2e44323345c5985ca613",
        "gate_source_commit": "ac9b6b18272b4ec94902db6cd98aaef2e39169eb",
        "training_runtime_authority_identity": "321a2f5d29bde8507214a891d6385a910888a8c528c1b1a9447ef7fcadbd741a",
        "training_receipt_identity": "23e32f06ccd290750007a70dce88ab64c402325db2851b08a206a6a6131619d2",
        "training": {
            "mode": "FULL",
            "optimizer": "PAGED_ADAMW_8BIT",
            "optimizer_steps": 40,
            "epochs": 1,
            "final_loss": "0.00068188272416591644",
            "compile_load_triton": True,
            "backward_4bit": True,
            "save_reload": True,
        },
        "adapter_materialization_sha256": {
            "A": "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b",
            "B": "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b",
        },
        "adapter_materializations_byte_identical": True,
        "development_sha256": "58590d6c63e71dd32149de73f77daf949c69183ee35fdb733d85b2915e5f3511",
        "development_gate": {
            "materialization_A_disposition_identity": "a8b418cafe653cf912a9b2e96a6598dc394409a47ab57a37f47ff13a7568d1c5",
            "materialization_B_disposition_identity": "86e7e9e5b303e038616754a0ae7ed0851b464df53dee3dcf0f9c67c3958cba76",
            "observation_rows_each": 48,
            "cross_materialization_observation_mismatches": 0,
            "terminal_eos_passed_each": 48,
            "canonical_json_passed_each": 48,
            "anti_repetition_passed_each": 48,
            "exact_target_diagnostic_only_each": 33,
            "status": "PASS",
        },
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return sealed(core, "adapter_audit_identity")


def candidate_manifest(receipt: dict[str, object]) -> dict[str, object]:
    core = {
        "schema": "pastila-production-core-candidate-object-manifest",
        "schema_version": 5,
        "status": "SUCCESSOR_CONTENT_ADDRESSED_AUTHORITY_NO_QUALIFICATION_EXECUTION",
        "source_commit": "ac9b6b18272b4ec94902db6cd98aaef2e39169eb",
        "base_model_manifest_sha256": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
        "tokenizer_sha256": "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c",
        "tokenizer_fix_mistral_regex": True,
        "adapter_manifest_sha256": {
            "pastila-editor-core-v1.1-json-successor-v2": "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b",
            "pastila-editor-core-v1.2-json-successor": "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719",
        },
        "training_receipt_identity": {
            "pastila-editor-core-v1.1-json-successor-v2": "23e32f06ccd290750007a70dce88ab64c402325db2851b08a206a6a6131619d2",
            "pastila-editor-core-v1.2-json-successor": "d362ab7d26e0bbb9793782ca294376b248de053fc3dbe4fc5740359cfdbf2acf",
        },
        "v1_1_adapter_audit_identity": receipt["adapter_audit_identity"],
        "training_runtime_authority_identity": "321a2f5d29bde8507214a891d6385a910888a8c528c1b1a9447ef7fcadbd741a",
        "qualification_authority_issued": False,
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return sealed(core, "manifest_identity")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt = audit_receipt()
    manifest = candidate_manifest(receipt)
    outputs = {
        "production-core-v1.1-successor-adapter-audit-receipt-v5.json": receipt,
        "production-core-successor-candidate-object-manifest-v5.json": manifest,
    }
    for name, value in outputs.items():
        (args.output_dir / name).write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n")
    print(receipt["adapter_audit_identity"])
    print(manifest["manifest_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
