"""Materialize the audited dual-successor V9 receipt and candidate manifest."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def sealed(core, field):
    return {**core, field: hashlib.sha256(canonical(core)).hexdigest()}


def audit_receipt():
    core = {
        "schema": "pastila-production-core-dual-successor-adapter-audit-receipt",
        "schema_version": 9,
        "status": "PASS_ZERO_QUALIFICATION_ATTEMPTS",
        "branch": "successor/core-v2-v9-dual-structural-remediation",
        "training_source_commit": "6da4edb718a27b14690ca8b0fd41b3597cb55524",
        "gate_source_commit": "60ddf3fad7bf1d5799fcf0918db5f3b58fa86811",
        "training_runtime_authority_identity": "6877f7596d0cafc9518681147f6880b7630bed6f7e23fc88a0d43aab15a2ed23",
        "adapters": {
            "pastila-editor-core-v1.1-json-successor-v9": {
                "training_receipt_identity": "14d0689b4f26b8398767a42ca84941cccddf1606a7861c1c478a5d6b8ac04d15",
                "content_identity": "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c",
                "materializations": {"A": "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c", "B": "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c"},
                "development_gate_identity": "660fcf43df35d9ba9c867d73cd0768486aa763074cb4468de185e787ce89cc1c",
                "development_rows": 72,
            },
            "pastila-editor-core-v1.2-json-successor-v9": {
                "training_receipt_identity": "08fb1990350e5db00df934ca54e1b3dd560df400ec1a3faf22f89bcf9edafcee",
                "content_identity": "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8",
                "materializations": {"A": "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8", "B": "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8"},
                "development_gate_identity": "a1e9fb380ffeaf5a19ab95763841a15f0b89c18925fc670cb75ee11bd283f915",
                "development_rows": 72,
            },
        },
        "materializations_byte_identical": True,
        "development_sha256": "9d276d4d49088ee52539a032874609de75d492027e2a6bfd70ec54da95f74059",
        "development_runner_sha256": "202610938673b9cb9202ee49f21dd427df4f5dbfae1945f3375c92de0aafb4c4",
        "development_launcher_sha256": "8e921f709cfb63cd75afa6b534a1c9c5bfef25b77357e8b72be04b992b730a18",
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return sealed(core, "adapter_audit_identity")


def candidate_manifest(receipt):
    core = {
        "schema": "pastila-production-core-candidate-object-manifest",
        "schema_version": 9,
        "status": "SUCCESSOR_CONTENT_ADDRESSED_AUTHORITY_NO_QUALIFICATION_EXECUTION",
        "source_commit": "60ddf3fad7bf1d5799fcf0918db5f3b58fa86811",
        "base_model_manifest_sha256": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
        "tokenizer_sha256": "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c",
        "tokenizer_fix_mistral_regex": True,
        "adapter_manifest_sha256": {
            "pastila-editor-core-v1.1-json-successor-v2": "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c",
            "pastila-editor-core-v1.2-json-successor": "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8",
        },
        "successor_candidate_identity": {
            "pastila-editor-core-v1.1-json-successor-v2": "pastila-editor-core-v1.1-json-successor-v9",
            "pastila-editor-core-v1.2-json-successor": "pastila-editor-core-v1.2-json-successor-v9",
        },
        "adapter_audit_identity": receipt["adapter_audit_identity"],
        "training_runtime_authority_identity": "6877f7596d0cafc9518681147f6880b7630bed6f7e23fc88a0d43aab15a2ed23",
        "qualification_authority_issued": False,
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return sealed(core, "manifest_identity")


def main():
    receipt = audit_receipt(); manifest = candidate_manifest(receipt)
    for name, value in (("production-core-dual-successor-adapter-audit-receipt-v9.json", receipt), ("production-core-successor-candidate-object-manifest-v9.json", manifest)):
        (ART / name).write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n")
    print(receipt["adapter_audit_identity"]); print(manifest["manifest_identity"])
    return 0


if __name__ == "__main__": raise SystemExit(main())
