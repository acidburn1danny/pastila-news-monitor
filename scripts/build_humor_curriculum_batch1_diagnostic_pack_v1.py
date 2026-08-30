"""Build and freeze the pre-baseline Batch 1 diagnostic evidence pack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".humor-mechanics-curriculum-v1-batch1-diagnostic-pack-v1-evidence"
UNSEEN = ROOT / ".pastilaacida-voice-v2-unseen-12-production-path-proof-v1-evidence" / "artifacts"
SUPPLEMENTAL = ROOT / ".pastilaacida-voice-v2-supplemental-8-proof-only-authority-v1-evidence" / "supplemental-8-project-v1.json.voice-v2" / "stories"
CURRICULUM = ROOT / "docs" / "artifacts" / "humor-mechanics-curriculum-v1.manifest.json"
PILOT = ROOT / ".humor-mechanics-curriculum-v1-batch1-historical-pilot-v1-evidence" / "manifest.json"


CASE_SPECS = {
    "1031": ("CULTURE_PUBLIC_NAMING", ["SARCASM", "IRONY", "CONTRAST_JUXTAPOSITION", "DEADPAN_OBSERVATION"], ["FRAME_TRANSFER"], False),
    "1308": ("ENVIRONMENTAL_MEASUREMENT", ["UNDERSTATEMENT", "DEADPAN_OBSERVATION", "COMIC_ANALOGY"], ["HYPERBOLE"], False),
    "1322": ("LAW_DIGITAL_RIGHTS", ["IRONY", "CONTRAST_JUXTAPOSITION", "REVERSAL"], ["SARCASM"], False),
    "1841": ("ENERGY_INFRASTRUCTURE", ["DEADPAN_OBSERVATION", "COMIC_ANALOGY", "CONTRAST_JUXTAPOSITION"], ["HYPERBOLE"], False),
    "1874": ("ALLEGATION_PUBLIC_AUTHORITY", ["IRONY", "SARCASM", "CONTRAST_JUXTAPOSITION"], ["HYPERBOLE"], True),
    "1877": ("PUBLIC_NAMING_PROPOSAL", ["IRONY", "DEADPAN_OBSERVATION", "REVERSAL"], ["FRAME_TRANSFER"], False),
    "1946": ("TRANSPORT_INFRASTRUCTURE", ["CONTRAST_JUXTAPOSITION", "UNDERSTATEMENT", "COMIC_ANALOGY"], ["ESCALATION"], False),
    "2068": ("LABOR_VIOLATION", ["SARCASM", "IRONY", "CONTRAST_JUXTAPOSITION"], ["HYPERBOLE"], False),
    "2148": ("ORDINARY_INFRASTRUCTURE_FAILURE", ["UNDERSTATEMENT", "DEADPAN_OBSERVATION", "COMIC_ANALOGY"], ["ESCALATION"], False),
    "607": ("EDUCATION_HUMAN_INTEREST", ["REVERSAL", "DEADPAN_OBSERVATION", "UNDERSTATEMENT"], ["SARCASM"], False),
    "641": ("ANIMAL_HUMAN_ABSURDITY", ["IRONY", "DEADPAN_OBSERVATION", "COMIC_ANALOGY", "REVERSAL"], ["HYPERBOLE"], False),
    "720": ("ENERGY_WORKFORCE", ["IRONY", "CONTRAST_JUXTAPOSITION", "REVERSAL", "DEADPAN_OBSERVATION"], ["SARCASM"], False),
    "1336": ("DEATH_MISSING_PERSON", [], ["SARCASM", "HYPERBOLE", "FRAME_TRANSFER"], True),
    "1705": ("CAPTIVITY_RELEASE", [], ["SARCASM", "HYPERBOLE", "FRAME_TRANSFER"], True),
    "2183": ("EXTREME_WEATHER", ["UNDERSTATEMENT", "DEADPAN_OBSERVATION", "COMIC_ANALOGY"], ["HYPERBOLE"], False),
    "597": ("SECURITY_MILITARY", [], ["SARCASM", "HYPERBOLE", "FRAME_TRANSFER"], True),
    "628": ("TRANSPORT_FIRE", ["UNDERSTATEMENT", "DEADPAN_OBSERVATION"], ["HYPERBOLE", "ESCALATION"], True),
    "978": ("EDUCATION_POLICY_UNCERTAINTY", ["IRONY", "UNDERSTATEMENT", "DEADPAN_OBSERVATION"], ["SARCASM"], False),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_source(event_id: str) -> tuple[Path, dict, str]:
    unseen = list(UNSEEN.glob(f"editor-{event_id}-*.json"))
    if unseen:
        path = unseen[0]
        value = json.loads(path.read_text(encoding="utf-8"))
        fact = value["operational_result"]["draft"]["stories"][0]["factual_summary"]
        return path, fact, "OWNER_ACCEPTED_PRODUCTION_PROOF"
    revisions = list((SUPPLEMENTAL / event_id / "revisions").glob("*.json"))
    if len(revisions) != 1:
        raise RuntimeError(f"expected one supplemental revision for {event_id}")
    path = revisions[0]
    value = json.loads(path.read_text(encoding="utf-8"))
    fact = value["authored_draft"]["stories"][0]["factual_summary"]
    return path, fact, "GOVERNED_CANONICAL_VOICE_STATE"


def build() -> None:
    if (OUTPUT / "baseline-results.json").exists():
        raise RuntimeError("baseline already exists; frozen diagnostic pack cannot be rebuilt")
    curriculum = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    cases, key = [], []
    for ordinal, (event_id, spec) in enumerate(CASE_SPECS.items(), 1):
        domain, allowed, inferior, abstention_valid = spec
        source, fact, provenance = load_source(event_id)
        text = fact["text"]
        case_id = f"HMCV1-B1-DIAG-{ordinal:02d}"
        cases.append({
            "case_id": case_id,
            "event_id": int(event_id),
            "factual_summary": text,
            "factual_summary_sha256": sha(text.encode("utf-8")),
            "authority_identity": fact["authority_bundle_identity"],
            "authority_byte_immutable": True,
            "source_artifact": str(source.relative_to(ROOT)),
            "source_artifact_sha256": sha(source.read_bytes()),
            "source_provenance": provenance,
        })
        key.append({
            "case_id": case_id,
            "semantic_domain": domain,
            "acceptable_mechanisms": allowed,
            "acceptable_combinations": "ANY_STORY_JUSTIFIED_SUBSET_OR_COMBINATION",
            "plausible_but_inferior_mechanisms": inferior,
            "justified_abstention": abstention_valid,
            "single_correct_mechanism": False,
            "diagnostic_checks": ["FACTUAL_BOUNDARY", "STORY_SPECIFICITY", "MECHANISM_FIT", "SYNTACTIC_DIVERSITY", "TARGET_DISCIPLINE", "ABSTENTION_JUDGMENT"],
        })
    pack = {
        "schema_name": "pastila-humor-mechanics-batch1-diagnostic-pack",
        "schema_version": "1.0.0",
        "lifecycle": "FROZEN_PRE_BASELINE",
        "curriculum_identity": curriculum["canonical_identity"],
        "historical_pilot_identity": pilot["canonical_identity"],
        "case_count": len(cases),
        "annotations_excluded_from_generation": True,
        "symmetric_mechanism_quotas": False,
        "synthetic_positives": 0,
        "historical_recovery_searches": 0,
        "cases": cases,
    }
    key_doc = {
        "schema_name": "pastila-humor-mechanics-batch1-diagnostic-evaluation-key",
        "schema_version": "1.0.0",
        "generation_path_access": "PROHIBITED",
        "owner_review_required": True,
        "cases": key,
        "historical_anchor_note": "The six frozen pilot records remain historical mechanism anchors, but were not executable cases because their ledger has no accepted factual input bytes. No recovery was performed.",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT / "generation-pack.json", pack)
    write_json(OUTPUT / "hidden-evaluation-key.json", key_doc)
    manifest = {
        "schema_name": "pastila-humor-mechanics-batch1-diagnostic-pack-manifest",
        "schema_version": "1.0.0",
        "pack_id": "HMCV1_BATCH1_DIAGNOSTIC_PACK_V1",
        "lifecycle": "FROZEN_PRE_BASELINE",
        "case_count": len(cases),
        "curriculum_identity": curriculum["canonical_identity"],
        "historical_pilot_identity": pilot["canonical_identity"],
        "generation_pack_sha256": sha((OUTPUT / "generation-pack.json").read_bytes()),
        "hidden_evaluation_key_sha256": sha((OUTPUT / "hidden-evaluation-key.json").read_bytes()),
        "builder_script_sha256": sha(Path(__file__).read_bytes()),
        "baseline_execution_count": 0,
        "curriculum_exposure": False,
        "runtime_modification": False,
        "training_authorized": False,
        "canonical_identity": None,
    }
    manifest["canonical_identity"] = sha(canonical({k: v for k, v in manifest.items() if k != "canonical_identity"}))
    write_json(OUTPUT / "pack-manifest.json", manifest)
    print(manifest["canonical_identity"])


if __name__ == "__main__":
    build()
