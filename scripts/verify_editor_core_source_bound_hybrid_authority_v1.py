from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).parents[1]
AUTH = ROOT / "docs/artifacts/editor-core-source-bound-hybrid-execution-authority-v1.json"
ARMS = ("B0_R2_ONE_PASS", "B1_EXTRACTIVE_BASELINE", "B2_HYBRID")
SEEDS = (161803, 271828, 314159)

def canonical(value): return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(arm=None, seed=None):
    value = json.loads(AUTH.read_text(encoding="utf-8")); identity = value.pop("authority_identity")
    if identity != hashlib.sha256(canonical(value)).hexdigest(): raise ValueError("authority identity")
    boundary = json.loads((ROOT / "docs/artifacts/editor-core-source-bound-hybrid-runtime-boundary-v1.json").read_text())
    if value["published_commit"] != "a44ab7be551da500f05ea4c10a5cf1f5eadd7212": raise ValueError("published commit")
    if value["runtime_boundary_identity"] != boundary["runtime_boundary_identity"]: raise ValueError("boundary identity")
    if value["pack_identity"] != boundary["pack_identity"] or value["protocol_identity"] != boundary["protocol_identity"]: raise ValueError("pack/protocol")
    if value["tokenizer_sha256"] != boundary["tokenizer_sha256"] or value["parent_adapter_identity"] != boundary["parent_adapter_identity"]: raise ValueError("tokenizer/parent")
    expected = {"worker_sha256": "editor_core_source_bound_hybrid_slot_v1.py",
                "supervisor_sha256": "supervise_editor_core_source_bound_hybrid_v1.py",
                "verifier_sha256": "verify_editor_core_source_bound_hybrid_authority_v1.py",
                "preflight_sha256": "preflight_editor_core_source_bound_hybrid_runtime_v1.py"}
    for key, name in expected.items():
        if value[key] != digest(ROOT / "scripts" / name): raise ValueError(key)
    if len(value["slots"]) != 9 or len({x["slot_id"] for x in value["slots"]}) != 9: raise ValueError("slot inventory")
    if {x["arm"] for x in value["slots"]} != set(ARMS) or {x["seed"] for x in value["slots"]} != set(SEEDS): raise ValueError("factorial")
    required_true = ("fresh_exact_tokenizer_zero_step_per_slot", "distinct_empty_output_root_per_slot",
                     "stop_on_first_failure", "atomic_receipts", "no_partial_eligible_evidence",
                     "b2_verifier_required", "b2_extractive_fallback_required", "owner_run_authorization_required")
    if not all(value[x] for x in required_true): raise ValueError("required invariant")
    if value["retry_authorized"] or value["real_runs_authorized_in_build_task"] or value["autonomous_ledger_construction_claimed"]: raise ValueError("forbidden authority")
    if arm is None: return {"authority_identity": identity, "slots": value["slots"]}
    found = [x for x in value["slots"] if x["arm"] == arm and x["seed"] == seed]
    if len(found) != 1: raise ValueError("unauthorized slot")
    return {"authority_identity": identity, "slot": found[0]}

if __name__ == "__main__": print(json.dumps({"status": "PASS", "blockers": 0, **verify()}, sort_keys=True))
