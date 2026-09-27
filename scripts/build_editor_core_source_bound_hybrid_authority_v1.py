from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
ARMS = ("B0_R2_ONE_PASS", "B1_EXTRACTIVE_BASELINE", "B2_HYBRID"); SEEDS = (161803, 271828, 314159)
def canonical(v): return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    boundary = json.loads((ROOT / "docs/artifacts/editor-core-source-bound-hybrid-runtime-boundary-v1.json").read_text())
    tree = subprocess.check_output(["git", "show", "-s", "--format=%T", "a44ab7be551da500f05ea4c10a5cf1f5eadd7212"], text=True).strip()
    slots = [{"slot_id": f"{arm}__seed_{seed}", "arm": arm, "seed": seed,
              "output_slug": f"{arm.lower()}__seed_{seed}", "run_limit": 1}
             for arm in ARMS for seed in SEEDS]
    core = {"schema": "editor-source-bound-hybrid-execution-authority", "schema_version": 1,
            "scope": "FEASIBILITY_UPPER_BOUND_3X3_ONLY", "published_commit": "a44ab7be551da500f05ea4c10a5cf1f5eadd7212",
            "published_tree": tree, "runtime_boundary_identity": boundary["runtime_boundary_identity"],
            "pack_identity": boundary["pack_identity"], "protocol_identity": boundary["protocol_identity"],
            "tokenizer_sha256": boundary["tokenizer_sha256"], "parent": "R2_STEP_9",
            "parent_adapter_identity": boundary["parent_adapter_identity"],
            "runtime_python": "/root/pf9-ml-runtime-20260926/bin/python",
            "runtime_python_sha256": "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f",
            "worker_sha256": digest(ROOT / "scripts/editor_core_source_bound_hybrid_slot_v1.py"),
            "supervisor_sha256": digest(ROOT / "scripts/supervise_editor_core_source_bound_hybrid_v1.py"),
            "verifier_sha256": digest(ROOT / "scripts/verify_editor_core_source_bound_hybrid_authority_v1.py"),
            "preflight_sha256": digest(ROOT / "scripts/preflight_editor_core_source_bound_hybrid_runtime_v1.py"),
            "slots": slots, "fresh_exact_tokenizer_zero_step_per_slot": True,
            "distinct_empty_output_root_per_slot": True, "b2_verifier_required": True,
            "b2_extractive_fallback_required": True, "atomic_receipts": True,
            "no_partial_eligible_evidence": True, "retry_authorized": False, "stop_on_first_failure": True,
            "owner_run_authorization_required": True, "real_runs_authorized_in_build_task": False,
            "oracle_fixture_upper_bound": True, "autonomous_ledger_construction_claimed": False,
            "successor_training": "SUSPENDED", "historical_holdouts_allowed": False,
            "parent_selection_authority": False, "promotion_authorized": False, "release_authorized": False,
            "voice_or_chief_editor_objective": False}
    value = {**core, "authority_identity": hashlib.sha256(canonical(core)).hexdigest()}
    output = ROOT / "docs/artifacts/editor-core-source-bound-hybrid-execution-authority-v1.json"
    output.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps({"status": "PASS_BUILD", "authority_identity": value["authority_identity"]}, sort_keys=True))

if __name__ == "__main__": main()
