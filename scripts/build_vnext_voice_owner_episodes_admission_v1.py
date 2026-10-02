import hashlib
import json
from pathlib import Path

SCHEMA = "vnext-voice-owner-written-episodes-admission-boundary"
EPISODES = {
    22: (15478, "49891e9da6d571f95df322715da17e05239560a62d47265ec2beb49dbdf90718", "TRAIN"),
    23: (11084, "36f799a92e8ea256473995dc2820ea25d3ea18dbc460a74a3f04cdd215e73d0e", "TRAIN"),
    24: (13033, "fe1d59a879b810f2b3369c18230bf82f26f9c1c35c721acb0947eb46347f67fc", "TRAIN"),
    25: (11373, "d9ac80c5f5db56f0e4697f3696e5f824582cb2782ae18994727a67441f5db5e1", "TRAIN"),
    26: (13303, "6f7872af2a625e3ddb0ad48bf8301d3b526463081d89873cb41d75e94b1f8c0f", "TRAIN"),
    27: (11433, "58904e57187b81d77d2389c3c7fb862084662e500c0f2a1205d71ce1a52cd8ae", "TRAIN"),
    28: (13458, "0f16ce6ce3f914bb0618c84566b25776f12fc44b21b3e8cf0b3f2b34bf83c012", "VALIDATION"),
    30: (23571, "1f32bb452276d1a9dba4fce55e368cfb667a5184761cdaff9204bbeaef658a71", "VALIDATION"),
    31: (18285, "429779895057340b1332376a76c9f8a21fa68def55bdc99acb2bcdbb02f01c44", "OWNER_BLIND_HOLDOUT"),
    32: (13493, "966f90b79e9b3d1a580b8fbebbe70c4efa650c715239eefb6bddf811a7666f69", "OWNER_BLIND_HOLDOUT"),
    33: (21536, "4ecf35a7a35a3dfd2b360754758b10c9221639ab05be9bb21587daf4e391934e", "OWNER_BLIND_HOLDOUT"),
    34: (13709, "c191f5afffae44db252741430f03afa7dea37de7967b628af921a4311ae659dc", "OWNER_BLIND_HOLDOUT"),
}
OUT = Path("docs/artifacts/vnext-voice-owner-episodes-admission-v1.json")

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def build(root: Path):
    sources = []
    for episode, (size, expected, split) in EPISODES.items():
        rel = f"docs/artifacts/vnext-voice-owner-episodes-v1/sources/episode-{episode}.txt"
        data = (root / rel).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if len(data) != size or actual != expected:
            raise ValueError(f"source identity mismatch: episode {episode}")
        sources.append({
            "episode": episode, "family_identity": f"PASTILA_ACIDA_EPISODE_{episode}",
            "path": rel, "bytes": size, "sha256": expected,
            "partition_reservation": split,
            "source_admission": "ADMITTED_OWNER_WRITTEN_FILMED_EPISODE",
            "training_rights": "GRANTED_BY_OWNER_IN_SESSION_2026-10-03",
            "record_level_training_eligibility": "PENDING_FACTUAL_COMMENTARY_SPAN_ADJUDICATION",
            "draft_final_status": ("OWNER_ATTESTED_FILMED_SOURCE_DRAFT_LABEL_RETAINED" if episode == 34 else "OWNER_ATTESTED_FILMED_SOURCE"),
        })
    curriculum = json.loads((root / "docs/artifacts/humor-mechanics-curriculum-v1.manifest.json").read_text(encoding="utf-8"))
    ids = []
    def walk(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k in {"mechanism_id", "id"} and isinstance(x, str) and x.startswith("HMCV1-"):
                    ids.append(x)
                walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    walk(curriculum)
    ids = sorted(set(ids))
    if len(ids) != 50:
        raise ValueError(f"expected 50 curriculum mechanisms, got {len(ids)}")
    evidenced = ["HMCV1-B01-M05-FRAME_TRANSFER", "HMCV1-B01-M08-ESCALATION", "HMCV1-B02-M10-ROLE_SIMULATION"]
    result = {
        "schema": SCHEMA, "schema_version": 1,
        "status": "PASS_SOURCE_RIGHTS_ADMISSION_DATASET_NOT_READY",
        "authority_parent": "705aaff7aac0d72dc1347bf9f60faba63670d916",
        "source_corpus": {
            "episodes": [22,23,24,25,26,27,28,30,31,32,33,34],
            "episode_29": "ABSENT_NOT_RECONSTRUCTED",
            "documents": 12, "bytes_admitted": sum(x[0] for x in EPISODES.values()),
            "sources": sources,
        },
        "rights_closure": {
            "status": "PASS_OWNER_AUTHOR_AND_RIGHTS_HOLDER_DECLARATION_BOUND_TO_EXACT_SOURCE_HASHES",
            "source_documents_training_authorized": 12,
            "uses": ["VOICE_DATASET_CONSTRUCTION", "HUMOR_MECHANICS_ANNOTATION", "TRAIN_VALIDATION_AFTER_PARTITION_GATE", "FUTURE_QWEN3_LORA_AFTER_REQUIRED_GATES"],
            "third_party_rights_claimed": False,
        },
        "factual_commentary_separation": {
            "status": "FAIL_CLOSED_PENDING_SPAN_LEVEL_ADJUDICATION",
            "source_bytes_admitted": sum(x[0] for x in EPISODES.values()),
            "training_rows_admitted": 0,
            "reason": "EPISODE_DOCUMENTS_INTERLEAVE_FACTUAL_SETUP_AND_OWNER_COMMENTARY_WITHOUT_AUTHORITATIVE_SPAN_LABELS",
            "episode_34_trailing_non_program_marker": "EXCLUDED_FROM_FUTURE_GOLD_UNLESS_OWNER_ADJUDICATES",
        },
        "partition": {
            "unit": "WHOLE_EPISODE_TRANSITIVE_FAMILY", "revision_colocation": True,
            "assignment_frozen_before_RECORD_CONSTRUCTION": True,
            "train": [22,23,24,25,26,27], "validation": [28,30], "owner_blind_holdout": [31,32,33,34],
            "qwen3_bakeoff": "PERMANENT_EVALUATION_ONLY_SEPARATE_HOLDOUT",
            "family_overlap": 0, "source_identity_overlap": 0,
        },
        "mechanism_annotation": {
            "curriculum": "HUMOR_MECHANICS_CURRICULUM_V1_FROZEN_50",
            "curriculum_is_training_corpus": False,
            "records_fully_annotated": 0,
            "source_level_evidence": [{"episode": 32, "authority": "humor-mechanics-curriculum-v1-batch2-m20-owner-freeze-v1", "mechanisms": evidenced, "training_eligible": False}],
            "evidence_backed_observed_mechanisms": evidenced,
            "positive_training_mechanisms": [],
            "positive_gaps": ids, "quota_fill": False,
        },
        "gold_commentary": {"train_rows": 0, "validation_rows": 0, "holdout_rows": 0, "characters": 0, "tokens_estimated": 0},
        "leakage_closure": {
            "status": "PASS_SOURCE_FAMILY_RESERVATION_ZERO_MODEL_VISIBLE_ROWS",
            "whole_family_isolation": True, "qwen3_bakeoff_training_exposure": False,
            "historical_development_evidence_training_exposure": False,
        },
        "factual_safety": {
            "constrained_projection": "RUNTIME_ONLY", "factual_authority": "RUNTIME_ONLY",
            "unsupported_fact_negatives_required": True, "abstention_examples_required": True,
            "status": "PENDING_RECORD_CONSTRUCTION",
        },
        "training_readiness": {
            "qwen3_lora": "NOT_READY", "training_performed": False, "weights_modified": False,
            "blockers": ["ZERO_SPAN_ADJUDICATED_GOLD_ROWS", "ZERO_TRAINING_POSITIVE_MECHANISM_COVERAGE", "NO_FACTUAL_SAFETY_NEGATIVE_SET", "NO_RECORD_LEVEL_DEDUPLICATION_OR_CONTAMINATION_AUDIT"],
        },
        "active_product_modified": False, "canonical_rollback_modified": False,
        "gui_state": "ACTIVE", "voice_state": "DISABLED_UNTIL_PROMOTION",
        "legacy_dependency_count": 0, "promotion": False, "active_integration": False,
    }
    result["result_identity"] = hashlib.sha256(canonical(result)).hexdigest()
    path = root / OUT
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for suffix in ("train", "validation"):
        (root / f"docs/artifacts/vnext-voice-owner-episodes-{suffix}-v1.jsonl").write_bytes(b"")
    return result

if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
