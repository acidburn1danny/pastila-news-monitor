"""Batch 2 V2 metadata-first, zero-construction discovery closure.

Partitions and family seals are computed before non-blind atom access. Blind
families never have title, summary, or fact-bundle content queried.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = "c756135fa9b822dd945728a2df05f26f3b44fa63"
PLAN_IDENTITY = "57419ff52730ccd20acf3c716c9502667d9f25e517570e18eeae7ec3d472da8a"
SUPERSEDED_INVENTORY_COMMIT = "bf2ed9a6b927170740576917315bc4c5d1c69290"
OWNER_FINAL_EVENT_IDS = (2096, 2472, 1538, 2111, 2360, 2617, 2365, 734)
PERMANENTLY_BLIND_CONTAMINATED = {1538, 2617}
PERMITTED_USE = {
    "observatornews": ("WRITTEN_PERMISSION_REQUIRED_NOT_PRESENT", "https://observatornews.ro/termeni-si-conditii.html"),
    "click": ("WRITTEN_PERMISSION_REQUIRED_NOT_PRESENT", "https://click.ro/termeni-si-conditii"),
    "oficiul_de_stiri": ("FUTURE_CONSTRUCTION_USE_UNRESOLVED", "https://oficiuldestiri.ro/termeni-si-conditii"),
    "tvr_info": ("NO_EXPLICIT_CONSTRUCTION_PERMISSION_FOUND", "https://tvrinfo.ro/p-biroul-juridic-lexoria-privind-drepturile-de-autor-asupra-continutului-de-pe-internet-este-posibil-sa-se-faca-text-sau-o-fotografie/"),
    "turnul_sfatului": ("NO_TERMS_RECORD_FOUND", None),
    "libertatea": ("NO_AFFIRMATIVE_CONSTRUCTION_PERMISSION_FOUND", "https://www.libertatea.ro/confidentialitate"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(namespace: str, payload: Any) -> str:
    body = json.dumps({"namespace": namespace, "payload": payload}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode()
    return sha(body)


def walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def event_family(event_id: int) -> str:
    return identity("B2V2_EVENT_FAMILY", {"event_id": event_id})


def partition(event_family_id: str) -> tuple[int, str]:
    score = int(sha((PLAN_IDENTITY + event_family_id).encode())[:8], 16) % 10
    return score, ("DEVELOPMENT" if score < 6 else "CURRICULUM_CANDIDATE" if score < 9 else "BLIND_EVALUATION")


def metadata_articles(db: sqlite3.Connection, event_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT id, source_id, normalized_url, published_at, discovered_at, event_id "
        "FROM articles WHERE event_id = ? ORDER BY id", (event_id,)
    ).fetchall()
    return [{"article_id": row["id"], "source_id": row["source_id"],
             "normalized_url_sha256": sha((row["normalized_url"] or "").encode()),
             "published_at": row["published_at"], "discovered_at": row["discovered_at"],
             "database_event_id": row["event_id"]} for row in rows]


def seals(event_id: int, articles: list[dict[str, Any]]) -> dict[str, str]:
    metadata = [{k: row[k] for k in ("article_id", "source_id", "normalized_url_sha256")} for row in articles]
    source = identity("B2V2_SOURCE_ARTIFACT_FAMILY_METADATA_ONLY", metadata)
    event = event_family(event_id)
    authority = identity("B2V2_AUTHORITY_ENVELOPE_FAMILY_METADATA_ONLY",
                         sorted({row["source_id"] for row in articles}))
    topic = identity("B2V2_TOPIC_ENTITY_FAMILY_OPAQUE", {"event_family_id": event})
    closure = identity("B2V2_FAMILY_CLOSURE", [source, event, authority, topic])
    return {"source_family_id": source, "event_family_id": event,
            "authority_envelope_family_id": authority, "topic_entity_family_id": topic,
            "family_closure_id": closure}


def load_atoms(directory: Path) -> list[dict[str, Any]]:
    documents: list[Any] = []
    for path in sorted(directory.glob("*.json")):
        if "mechanic" in path.name or "expression" in path.name:
            continue
        try:
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    atoms: dict[str, dict[str, Any]] = {}
    for document in documents:
        for item in walk(document):
            atom = item.get("resulting_atom") or item.get("atom") or (item if item.get("atom_id") else None)
            if not isinstance(atom, dict) or not atom.get("atom_id"):
                continue
            exact = atom.get("exact_span") or atom.get("passage")
            evidence = atom.get("evidence")
            if not evidence and exact is not None:
                evidence = [{"passage": exact, "source_identity": atom.get("source_identity"),
                             "start": atom.get("start"), "end": atom.get("end")}]
            if evidence:
                atoms[atom["atom_id"]] = {
                    "atom_id": atom["atom_id"],
                    "evidence": evidence if isinstance(evidence, list) else [evidence],
                    "qualification": bool(atom.get("qualification") or atom.get("qualifications") or
                                          atom.get("qualification_target_atom_ids") or
                                          atom.get("uncertainty_target_atom_ids")),
                }
    return [atoms[key] for key in sorted(atoms)]


def source_ref(value: str | None) -> tuple[int, str] | None:
    match = re.fullmatch(r"article:(\d+):[^:]+:field:(title|summary)", value or "")
    return (int(match.group(1)), match.group(2)) if match else None


def occurrences(text: str, passage: str) -> list[int]:
    result, start = [], 0
    while passage and (found := text.find(passage, start)) >= 0:
        result.append(found)
        start = found + 1
    return result


def validate_evidence(db: sqlite3.Connection, event_id: int, atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = db.execute("SELECT id, title, summary FROM articles WHERE event_id = ? ORDER BY id", (event_id,)).fetchall()
    fields = {(row["id"], name): row[name] or "" for row in rows for name in ("title", "summary")}
    results = []
    for atom in atoms:
        for evidence in atom["evidence"]:
            passage = evidence.get("passage") or evidence.get("exact_span") or ""
            requested = source_ref(evidence.get("source_identity"))
            candidates = [requested] if requested in fields else list(fields)
            matches = [(article, field, offset) for article, field in candidates
                       for offset in occurrences(fields[(article, field)], passage)]
            unique = len(matches) == 1
            canonical_char = canonical_byte = None
            recorded_char_valid = recorded_byte_valid = False
            boundary_valid = True
            if unique:
                article, field, start = matches[0]
                text = fields[(article, field)]
                end = start + len(passage)
                canonical_char = [start, end]
                canonical_byte = [len(text[:start].encode()), len(text[:end].encode())]
            rec_start, rec_end = evidence.get("start"), evidence.get("end")
            if requested in fields and isinstance(rec_start, int) and isinstance(rec_end, int):
                text = fields[requested]
                recorded_char_valid = text[rec_start:rec_end] == passage
                try:
                    recorded_byte_valid = text.encode()[rec_start:rec_end].decode() == passage
                except UnicodeDecodeError:
                    boundary_valid = False
            status = ("RECORDED_CHARACTER_COORDINATES_VALID" if recorded_char_valid else
                      "RECORDED_UTF8_BYTE_COORDINATES_VALID" if recorded_byte_valid else
                      "STALE_COORDINATES_UNIQUE_BYTE_EXACT_RECOVERY" if unique and requested else
                      "UNBOUND_UNIQUE_BYTE_EXACT_RECOVERY" if unique else
                      "AMBIGUOUS_BYTE_EXACT_MATCH" if matches else "TARGET_BYTES_ABSENT")
            results.append({
                "atom_id": atom["atom_id"], "passage_sha256": sha(passage.encode()),
                "recorded_source_identity_sha256": sha((evidence.get("source_identity") or "").encode()),
                "recorded_character_coordinates_valid": recorded_char_valid,
                "recorded_utf8_byte_coordinates_valid": recorded_byte_valid,
                "recorded_utf8_boundaries_valid": boundary_valid,
                "unique_exact_match": unique, "canonical_character_coordinates": canonical_char,
                "canonical_utf8_byte_coordinates": canonical_byte, "status": status,
                "qualification_binding_present": atom["qualification"],
            })
    return results


def prior_filename_exposure(event_id: int) -> bool:
    needles = (f"story-{event_id}", f"event-{event_id}", f"story_{event_id}", f"event_{event_id}")
    return any(any(needle in path.name.lower() for needle in needles) for path in ROOT.iterdir())


def replacement_blind(db: sqlite3.Connection, count: int = 2) -> list[dict[str, Any]]:
    result = []
    event_ids = [row[0] for row in db.execute(
        "SELECT event_id FROM articles WHERE event_id IS NOT NULL GROUP BY event_id ORDER BY event_id")]
    for event_id in event_ids:
        if event_id in OWNER_FINAL_EVENT_IDS or prior_filename_exposure(event_id):
            continue
        articles = metadata_articles(db, event_id)
        family = seals(event_id, articles)
        score, assigned = partition(family["event_family_id"])
        if assigned != "BLIND_EVALUATION" or not articles:
            continue
        result.append({**family, "partition": assigned, "partition_score": score,
                       "opaque_holdout": True, "event_id_commitment": sha(str(event_id).encode()),
                       "metadata_article_count": len(articles),
                       "status": "PRISTINE_BLIND_EVALUATION_RESERVED_METADATA_ONLY",
                       "content_queries": 0, "atom_reads": 0, "construction_eligible": False})
        if len(result) == count:
            break
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    database_path = ROOT / "data" / "news_monitor.db"
    db = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    directories = {}
    for path in ROOT.glob(".pastilaacida-voice-v2-eeup-*-story-*-fact-finalization-v1-evidence"):
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        directories[int(manifest.get("event_id") or manifest.get("story_id"))] = path
    families, ledger = [], []
    for event_id in OWNER_FINAL_EVENT_IDS:
        directory = directories[event_id]
        manifest_bytes = (directory / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        articles = metadata_articles(db, event_id)
        family = seals(event_id, articles)
        score, assigned = partition(family["event_family_id"])
        if event_id in PERMANENTLY_BLIND_CONTAMINATED:
            families.append({**family, "partition": "BLIND_CONTAMINATED", "original_partition": assigned,
                             "partition_score": score, "opaque_holdout": True,
                             "event_id": event_id,
                             "event_id_commitment": sha(str(event_id).encode()),
                             "status": "PERMANENTLY_BLIND_CONTAMINATED_NO_REASSIGNMENT_NO_DOWNSTREAM_USE",
                             "permitted_use_closure": "NOT_REOPENED_BLIND_CONTAMINATION_IS_DISPOSITIVE",
                             "immutable_capture_closure": "NOT_REOPENED_BLIND_CONTAMINATION_IS_DISPOSITIVE",
                             "content_queries_this_pass": 0, "atom_reads_this_pass": 0,
                             "construction_eligible": False})
            ledger.append({"event_id_commitment": sha(str(event_id).encode()),
                           "classification": "BLIND_CONTAMINATED_PERMANENT",
                           "cause": "PRE_SEAL_ATOM_ACCESS_IN_SUPERSEDED_DISCOVERY_PASS",
                           "first_recorded_commit": SUPERSEDED_INVENTORY_COMMIT,
                           "reassignment_prohibited": True, "downstream_use_prohibited": True})
            continue
        atoms = load_atoms(directory)
        checks = validate_evidence(db, event_id, atoms)
        permissions = [{"source_id": source,
                        "status": PERMITTED_USE.get(source, ("NO_REVIEW_RECORD", None))[0],
                        "terms_url": PERMITTED_USE.get(source, (None, None))[1]}
                       for source in sorted({a["source_id"] for a in articles})]
        immutable = "HASH_BOUND_BUT_SOURCE_BYTES_NOT_ARCHIVED_IN_GIT"
        final_partition = assigned if assigned != "BLIND_EVALUATION" else "REJECTED"
        families.append({
            **family, "partition": final_partition, "original_partition": assigned,
            "partition_score": score, "event_id": event_id, "manifest_sha256": sha(manifest_bytes),
            "fact_bundle_identity": manifest.get("fact_atom_bundle_identity"),
            "metadata_articles": articles, "accepted_atom_count": len(atoms), "span_checks": checks,
            "coordinate_validation": "CHARACTER_AND_UTF8_BYTE_INDEPENDENT",
            "exact_target_bytes_uniquely_recoverable": bool(checks) and all(x["unique_exact_match"] for x in checks),
            "immutable_capture_status": immutable, "permitted_use_reviews": permissions,
            "status": "PROVISIONAL" if final_partition != "REJECTED" else "REJECTED_PRIOR_EXPOSURE_IN_BLIND_BUCKET",
            "construction_eligible": False,
            "construction_blockers": ["NO_AFFIRMATIVE_PERMITTED_USE", immutable,
                                      "PRIOR_OWNER_FACT_REVIEW_EXPOSURE", "G01B_NOT_AUTHORIZED"],
            "creative_premise_family_id": "UNASSIGNED",
            "construction_lineage_family_id": "UNASSIGNED", "revision_family_id": "UNASSIGNED",
        })
        ledger.append({"event_id": event_id, "classification": "KNOWN_NONBLIND_PRIOR_EXPOSURE",
                       "owner_fact_review": True, "batch2_constructor_exposure": False,
                       "model_exposure": False})
    replacements = replacement_blind(db)
    ledger.extend({
        "event_id_commitment": item["event_id_commitment"],
        "family_closure_id": item["family_closure_id"],
        "classification": "PRISTINE_BLIND_EVALUATION_RESERVED_METADATA_ONLY",
        "content_exposure": False,
        "atom_exposure": False,
        "constructor_exposure": False,
        "model_exposure": False,
    } for item in replacements)
    output = {
        "schema_name": "pastila-humor-mechanics-batch2-v2-source-discovery-closure",
        "schema_version": "2.0.0", "plan_commit": PLAN_COMMIT, "plan_identity": PLAN_IDENTITY,
        "supersedes_inventory_commit": SUPERSEDED_INVENTORY_COMMIT,
        "database_sha256": sha(database_path.read_bytes()), "families": families,
        "replacement_blind_evaluation_families": replacements,
        "contamination_exposure_ledger": ledger,
        "canonical_inventory": {
            "DEVELOPMENT": [f["family_closure_id"] for f in families if f["partition"] == "DEVELOPMENT"],
            "CURRICULUM_CANDIDATE": [f["family_closure_id"] for f in families if f["partition"] == "CURRICULUM_CANDIDATE"],
            "BLIND_EVALUATION": [f["family_closure_id"] for f in replacements],
            "PROVISIONAL": [f["family_closure_id"] for f in families if f["status"] == "PROVISIONAL"],
            "BLIND_CONTAMINATED": [f["family_closure_id"] for f in families if f["partition"] == "BLIND_CONTAMINATED"],
            "REJECTED": [f["family_closure_id"] for f in families if f["partition"] == "REJECTED"],
        },
        "eligibility": {"later_construction_decision": [],
                        "priority_mechanism_positive_gaps": ["M11", "M12", "M13", "M17", "M18", "M19"],
                        "reason": "NO_FAMILY_CLOSES_PERMITTED_USE_AND_IMMUTABLE_CAPTURE"},
        "authority": {"source_discovery": True, "construction": False, "surface_generation": False,
                      "model_exposure": False, "training": False, "runtime_integration": False,
                      "production_routing": False},
        "execution": {"database_mode": "READ_ONLY", "blind_content_queries": 0,
                      "blind_atom_reads": 0, "candidate_surfaces_created": 0, "model_calls": 0},
        "pipeline_invariants": {
            "metadata_family_seal_precedes_partition": True,
            "partition_precedes_atom_access": True,
            "blind_branch_precedes_atom_access": True,
            "blind_replacement_selection_metadata_only": True,
            "character_and_utf8_coordinates_independently_validated": True,
            "internally_sealed_does_not_imply_construction_ready": True,
        },
    }
    encoded = (json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if args.output:
        args.output.write_bytes(encoded)
    else:
        print(encoded.decode(), end="")


if __name__ == "__main__":
    main()
