import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
def main():
    subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build_editor_core_source_bound_hybrid_authority_v1.py")], check=True, capture_output=True)
    authority = json.loads((ROOT / "docs/artifacts/editor-core-source-bound-hybrid-execution-authority-v1.json").read_text())
    checks = [len(authority["slots"]) == 9, len({x["slot_id"] for x in authority["slots"]}) == 9,
              len({x["output_slug"] for x in authority["slots"]}) == 9, not authority["retry_authorized"],
              authority["stop_on_first_failure"], authority["atomic_receipts"], authority["no_partial_eligible_evidence"],
              authority["b2_verifier_required"], authority["b2_extractive_fallback_required"],
              authority["oracle_fixture_upper_bound"], not authority["autonomous_ledger_construction_claimed"],
              not authority["real_runs_authorized_in_build_task"], not authority["parent_selection_authority"]]
    supervisor = ROOT / "scripts/supervise_editor_core_source_bound_hybrid_v1.py"
    absent = ROOT / "NEVER_CREATED_HYBRID_AUTHORITY_FIXTURE"
    blocked = ROOT / "NEVER_CREATED_HYBRID_AUTHORITY_BLOCKED"
    if absent.exists() or blocked.exists(): raise ValueError("audit sentinel already exists")
    fixture = subprocess.run([sys.executable, "-B", str(supervisor), "--output-root", str(absent), "--fixture-only"],
                             capture_output=True, text=True, check=True)
    result = json.loads(fixture.stdout); checks += [result["slots"] == 9, result["distinct_outputs"] == 9, not absent.exists()]
    refusal = subprocess.run([sys.executable, "-B", str(supervisor), "--output-root", str(blocked)],
                             capture_output=True, text=True)
    checks += [refusal.returncode != 0, "separate owner authorization required" in refusal.stderr, not blocked.exists()]
    status = "PASS" if all(checks) else "BLOCKED"
    print(json.dumps({"status": status, "blockers": 0 if all(checks) else 1, "checks": len(checks),
                      "model_loaded": False, "inference_performed": False, "optimizer_created": False,
                      "training_performed": False}, sort_keys=True))
    raise SystemExit(0 if all(checks) else 1)
if __name__ == "__main__": main()
