"""Build and freeze the bounded semantic-admission/specificity contrast pack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".humor-mechanics-curriculum-v1-batch1-diagnostic-pack-v1-evidence"
OUTPUT = ROOT / ".humor-mechanics-curriculum-v1-semantic-admission-specificity-contrast-pack-v1-evidence"
SELECTED = ["HMCV1-B1-DIAG-08", "HMCV1-B1-DIAG-09", "HMCV1-B1-DIAG-10",
            "HMCV1-B1-DIAG-02", "HMCV1-B1-DIAG-03", "HMCV1-B1-DIAG-06",
            "HMCV1-B1-DIAG-07", "HMCV1-B1-DIAG-11", "HMCV1-B1-DIAG-12",
            "HMCV1-B1-DIAG-18"]
PACK_ID = "HMCV1_SEMANTIC_ADMISSION_SPECIFICITY_CONTRAST_V1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build() -> None:
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise RuntimeError("contrast pack already exists; rebuilding a frozen artifact is prohibited")
    source_manifest = json.loads((SOURCE / "pack-manifest.json").read_text(encoding="utf-8"))
    source_pack = json.loads((SOURCE / "generation-pack.json").read_text(encoding="utf-8"))
    run5 = json.loads((SOURCE / "baseline-run5-results.json").read_text(encoding="utf-8"))
    source_cases = {c["case_id"]: c for c in source_pack["cases"]}
    attempts = {a["case_id"]: a for a in run5["attempts"]}
    cases = []
    for ordinal, source_id in enumerate(SELECTED, 1):
        source = source_cases[source_id]
        cases.append({
            "case_id": f"HMCV1-SASC-{ordinal:02d}",
            "source_case_id": source_id,
            "event_id": source["event_id"],
            "factual_summary": source["factual_summary"],
            "factual_summary_sha256": source["factual_summary_sha256"],
            "authority_identity": source["authority_identity"],
            "authority_byte_immutable": True,
            "source_artifact": source["source_artifact"],
            "source_artifact_sha256": source["source_artifact_sha256"],
            "source_provenance": source["source_provenance"],
        })
    pack = {
        "schema_name": "pastila-semantic-admission-specificity-contrast-generation-pack",
        "schema_version": "1.0.0", "pack_id": PACK_ID, "lifecycle": "FROZEN_PRE_EXECUTION",
        "source_diagnostic_pack_identity": source_manifest["canonical_identity"],
        "case_count": len(cases), "annotations_excluded_from_generation": True,
        "single_correct_wording": False, "single_correct_mechanism": False,
        "curriculum_exposure": False, "cases": cases,
    }
    anchor_classes = {
        "HMCV1-B1-DIAG-08": ("A", "STORY_SPECIFIC_NONFACTUAL_TRANSFORMATION", "OWNER_QUALITY_CANDIDATE"),
        "HMCV1-B1-DIAG-09": ("B", "FACT_SAFE_BUT_PORTABLE_GENERIC", "REJECT_GENERIC_PORTABLE"),
        "HMCV1-B1-DIAG-10": ("C", "UNSUPPORTED_LIFE_HISTORY_INFERENCE", "REJECT_UNSUPPORTED_INFERENCE"),
    }
    profiles = {
        "HMCV1-B1-DIAG-02": ["PORTABLE_ENVIRONMENTAL_ANALOGY", "STORY_SPECIFICITY"],
        "HMCV1-B1-DIAG-03": ["UNSUPPORTED_POLICY_INTENT", "FACTUAL_SAFETY"],
        "HMCV1-B1-DIAG-06": ["POLICY_RECOMMENDATION_AS_COMMENTARY", "PORTABILITY"],
        "HMCV1-B1-DIAG-07": ["ENTITY_REUSE", "STORY_LOCAL_TRANSFORMATION"],
        "HMCV1-B1-DIAG-11": ["FICTION_RETURNING_AS_FACT", "STORY_SPECIFICITY"],
        "HMCV1-B1-DIAG-12": ["UNSUPPORTED_LIFE_HISTORY", "FACTUAL_SAFETY"],
        "HMCV1-B1-DIAG-18": ["UNSUPPORTED_FUTURE_OR_POLICY_INFERENCE", "PORTABILITY"],
    }
    hidden = []
    for case in cases:
        source_id = case["source_case_id"]
        record = {
            "case_id": case["case_id"], "source_case_id": source_id,
            "evaluation_dimensions": ["SPECIFICITY", "PORTABILITY", "UNSUPPORTED_INFERENCE", "FACTUAL_SAFETY", "ADMISSION_RESULT", "OWNER_QUALITY"],
            "multiple_valid_realizations": True, "single_correct_mechanism_or_wording": False,
            "diagnostic_profile": ([anchor_classes[source_id][1]] if source_id in anchor_classes else profiles[source_id]),
        }
        if source_id in anchor_classes:
            old = attempts[source_id]
            cls, label, disposition = anchor_classes[source_id]
            record["frozen_run5_anchor"] = {
                "contrast_class": cls, "class_label": label, "owner_disposition": disposition,
                "raw_output": old["raw_output"], "raw_output_sha256": old["raw_output_sha256"],
                "accepted_commentary": old["accepted_commentary"],
            }
        hidden.append(record)
    key = {
        "schema_name": "pastila-semantic-admission-specificity-contrast-hidden-key",
        "schema_version": "1.0.0", "generation_path_access": "PROHIBITED",
        "frozen_before_execution": True,
        "contrast_classes": {"A": "story-specific nonfactual transformation", "B": "fact-safe but portable/generic commentary", "C": "unsupported factual or life-history inference disguised as commentary"},
        "paired_contrasts": [
            {"cases": ["HMCV1-SASC-01", "HMCV1-SASC-02"], "purpose": "story-specific transformation versus portable thematic language"},
            {"cases": ["HMCV1-SASC-02", "HMCV1-SASC-03"], "purpose": "generic-but-fact-safe versus unsupported inference"},
            {"cases": ["HMCV1-SASC-07", "HMCV1-SASC-09"], "purpose": "story-local detail versus unsupported life-history inference"},
            {"cases": ["HMCV1-SASC-08", "HMCV1-SASC-10"], "purpose": "marked fiction risk versus unsupported future/policy inference"},
        ], "cases": hidden,
    }
    OUTPUT.mkdir(parents=True)
    write(OUTPUT / "generation-pack.json", pack)
    write(OUTPUT / "hidden-evaluation-key.json", key)
    manifest = {
        "schema_name": "pastila-semantic-admission-specificity-contrast-manifest", "schema_version": "1.0.0",
        "pack_id": PACK_ID, "lifecycle": "FROZEN_PRE_EXECUTION", "case_count": len(cases),
        "source_diagnostic_pack_identity": source_manifest["canonical_identity"],
        "source_run5_identity": run5["journal_identity"],
        "generation_pack_sha256": sha((OUTPUT / "generation-pack.json").read_bytes()),
        "hidden_evaluation_key_sha256": sha((OUTPUT / "hidden-evaluation-key.json").read_bytes()),
        "builder_script_sha256": sha(Path(__file__).read_bytes()),
        "execution_count": 0, "curriculum_exposure": False, "training_authority": False,
        "runtime_modification": False, "canonical_identity": None,
    }
    manifest["canonical_identity"] = sha(canonical({k: v for k, v in manifest.items() if k != "canonical_identity"}))
    write(OUTPUT / "pack-manifest.json", manifest)
    print(manifest["canonical_identity"])


if __name__ == "__main__":
    build()
