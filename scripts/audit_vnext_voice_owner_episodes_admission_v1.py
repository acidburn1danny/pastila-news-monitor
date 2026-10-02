import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_vnext_voice_owner_episodes_admission_v1 import OUT, build, canonical

def audit(root: Path):
    result = build(root)
    checks = {
        "twelve_exact_sources": result["source_corpus"]["documents"] == 12,
        "episode_29_absent": result["source_corpus"]["episode_29"] == "ABSENT_NOT_RECONSTRUCTED",
        "rights_bound_to_hashes": result["rights_closure"]["source_documents_training_authorized"] == 12,
        "family_partition_disjoint": result["partition"]["family_overlap"] == 0,
        "no_unadjudicated_training_rows": result["gold_commentary"]["train_rows"] == 0,
        "curriculum_not_training_corpus": result["mechanism_annotation"]["curriculum_is_training_corpus"] is False,
        "qwen_bakeoff_unexposed": result["leakage_closure"]["qwen3_bakeoff_training_exposure"] is False,
        "training_fail_closed": result["training_readiness"]["qwen3_lora"] == "NOT_READY",
        "protected_state": not result["active_product_modified"] and not result["canonical_rollback_modified"],
    }
    audit_doc = {"schema": "vnext-voice-owner-written-episodes-admission-audit", "schema_version": 1,
                 "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                 "result_identity": result["result_identity"]}
    audit_doc["audit_identity"] = hashlib.sha256(canonical(audit_doc)).hexdigest()
    (root / "docs/artifacts/vnext-voice-owner-episodes-admission-v1-audit.json").write_text(json.dumps(audit_doc, indent=2, sort_keys=True)+"\n")
    if audit_doc["status"] != "PASS": raise SystemExit(1)
    return audit_doc

if __name__ == "__main__": audit(Path(__file__).resolve().parents[1])
