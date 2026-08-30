"""Read-only Batch 2 V2 source-family discovery audit.

This utility inspects owner-final factual atom bundles and the local article store.
It never reads humor/mechanic candidate packets, creates surfaces, or writes files.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
PLAN_IDENTITY = "57419ff52730ccd20acf3c716c9502667d9f25e517570e18eeae7ec3d472da8a"
DIR_PATTERN = ".pastilaacida-voice-v2-eeup-*-story-*-fact-finalization-v1-evidence"
INVALIDATED_BLIND_EVENT_IDS = {1538, 2617}


def canonical_identity(namespace: str, payload: Any) -> str:
    body = json.dumps(
        {"namespace": namespace, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def partition(event_family_id: str) -> tuple[int, str]:
    score = int(hashlib.sha256((PLAN_IDENTITY + event_family_id).encode()).hexdigest()[:8], 16) % 10
    if score < 6:
        return score, "DEVELOPMENT"
    if score < 9:
        return score, "CURRICULUM_CANDIDATE"
    return score, "BLIND_EVALUATION"


def load_atoms(directory: Path) -> list[dict[str, Any]]:
    atoms: dict[str, dict[str, Any]] = {}
    documents: list[Any] = []
    for path in sorted(directory.glob("*.json")):
        if "mechanic" in path.name or "expression" in path.name:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        documents.append(value)
        for item in walk(value):
            atom = item.get("resulting_atom") or item.get("atom")
            if atom is None and item.get("atom_id") and item.get("evidence"):
                atom = item
            if not isinstance(atom, dict) or not atom.get("atom_id") or not atom.get("evidence"):
                continue
            atoms[atom["atom_id"]] = atom
    evidence_by_candidate: dict[str, dict[str, Any]] = {}
    for value in documents:
        for item in walk(value):
            candidate = item.get("candidate_id") or item.get("candidate_identity")
            evidence = item.get("evidence")
            if candidate and isinstance(evidence, dict) and evidence.get("source_identity"):
                evidence_by_candidate[candidate] = evidence
            elif candidate and item.get("source_identity") and item.get("exact_span") is not None:
                offsets = item.get("offsets") or [item.get("start"), item.get("end")]
                if None not in offsets:
                    evidence_by_candidate[candidate] = {
                        "source_identity": item["source_identity"],
                        "start": offsets[0],
                        "end": offsets[1],
                        "passage": item["exact_span"],
                    }
    for value in documents:
        for item in walk(value):
            if not item.get("atom_id") or item.get("atom_id") in atoms or item.get("exact_span") is None:
                continue
            candidate = item.get("candidate_id") or item.get("candidate_identity")
            evidence = evidence_by_candidate.get(candidate)
            if evidence is None and item.get("source_identity"):
                offsets = item.get("offsets") or [item.get("start"), item.get("end")]
                if None not in offsets:
                    evidence = {
                        "source_identity": item["source_identity"],
                        "start": offsets[0],
                        "end": offsets[1],
                        "passage": item["exact_span"],
                    }
            if evidence:
                atoms[item["atom_id"]] = {
                    "atom_id": item["atom_id"],
                    "kind": item.get("atom_kind") or item.get("canonical_fact_type", "").lower(),
                    "evidence": [evidence],
                    "qualification_target_atom_ids": ["RECORDED"] if item.get("qualification") or item.get("qualifications") else [],
                }
    return [atoms[key] for key in sorted(atoms)]


def article_id(source_identity: str) -> int | None:
    match = re.fullmatch(r"article:(\d+):[^:]+:field:(title|summary)", source_identity)
    return int(match.group(1)) if match else None


def main() -> None:
    database_path = ROOT / "data" / "news_monitor.db"
    database_sha256 = hashlib.sha256(database_path.read_bytes()).hexdigest()
    db = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    families: list[dict[str, Any]] = []

    for directory in sorted(ROOT.glob(DIR_PATTERN)):
        manifest_path = directory / "manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        event_id = int(manifest.get("event_id") or manifest.get("story_id"))
        event_family_id = canonical_identity("B2V2_EVENT_FAMILY", {"event_id": event_id})
        score, assigned_partition = partition(event_family_id)
        is_blind = assigned_partition == "BLIND_EVALUATION"
        atoms = [] if is_blind else load_atoms(directory)
        authority_ids = sorted(
            {
                evidence["authority_identity"]
                for atom in atoms
                for evidence in atom.get("evidence", [])
                if evidence.get("authority_identity")
            }
        )
        source_ids = sorted(
            {
                evidence["source_identity"]
                for atom in atoms
                for evidence in atom.get("evidence", [])
                if evidence.get("source_identity")
            }
        )
        article_ids = sorted({value for source in source_ids if (value := article_id(source)) is not None})
        articles = []
        span_results = []
        for identifier in article_ids:
            row = db.execute(
                "SELECT id, source_id, normalized_url, published_at, discovered_at, event_id, title, summary "
                "FROM articles WHERE id = ?",
                (identifier,),
            ).fetchone()
            if row is None:
                articles.append({"article_id": identifier, "status": "MISSING_FROM_CURRENT_DATABASE"})
                continue
            articles.append(
                {
                    "article_id": identifier,
                    "source_id": row["source_id"],
                    "normalized_url_sha256": hashlib.sha256(row["normalized_url"].encode()).hexdigest(),
                    "published_at": row["published_at"],
                    "discovered_at": row["discovered_at"],
                    "database_event_id": row["event_id"],
                }
            )
            fields = {"title": row["title"], "summary": row["summary"] or ""}
            for atom in atoms:
                for evidence in atom.get("evidence", []):
                    if article_id(evidence.get("source_identity", "")) != identifier:
                        continue
                    field = evidence["source_identity"].rsplit(":", 1)[-1]
                    text = fields[field]
                    start, end = evidence["start"], evidence["end"]
                    expected = evidence.get("passage", "")
                    character_observed = text[start:end]
                    encoded = text.encode("utf-8")
                    byte_boundary = True
                    try:
                        byte_observed = encoded[start:end].decode("utf-8")
                    except UnicodeDecodeError:
                        byte_boundary = False
                        byte_observed = ""
                    coordinate_convention = (
                        "CHARACTER" if character_observed == expected else
                        "UTF8_BYTE" if byte_observed == expected else
                        "NO_EXACT_MATCH"
                    )
                    span_results.append(
                        {
                            "atom_id": atom["atom_id"],
                            "source_identity": evidence["source_identity"],
                            "character_span": [start, end],
                            "utf8_span": [len(text[:start].encode()), len(text[:end].encode())],
                            "passage_sha256": hashlib.sha256(expected.encode()).hexdigest(),
                            "exact_match": coordinate_convention != "NO_EXACT_MATCH",
                            "coordinate_convention": coordinate_convention,
                            "utf8_boundaries_valid": byte_boundary,
                            "kind": atom.get("kind"),
                            "has_qualification_binding": bool(
                                atom.get("qualification_target_atom_ids") or atom.get("uncertainty_target_atom_ids")
                            ),
                        }
                    )

        source_artifact_family_id = canonical_identity(
            "B2V2_SOURCE_ARTIFACT_FAMILY", {"event_id": event_id, "source_ids": source_ids}
        )
        authority_family_id = canonical_identity("B2V2_AUTHORITY_FAMILY", authority_ids)
        topic_entity_family_id = canonical_identity(
            "B2V2_TOPIC_ENTITY_FAMILY", {"event_id": event_id, "article_ids": article_ids}
        )
        family_closure_id = canonical_identity(
            "B2V2_FAMILY_CLOSURE",
            [source_artifact_family_id, event_family_id, authority_family_id, topic_entity_family_id],
        )
        content = {
            "source_family_id": source_artifact_family_id,
            "event_family_id": event_family_id,
            "authority_envelope_family_id": authority_family_id,
            "topic_entity_family_id": topic_entity_family_id,
            "family_closure_id": family_closure_id,
            "creative_premise_family_id": "UNASSIGNED_REQUIRES_G01B_BEFORE_CONSTRUCTION",
            "construction_lineage_family_id": "UNASSIGNED_REQUIRES_G01B_BEFORE_CONSTRUCTION",
            "revision_family_id": "UNASSIGNED_REQUIRES_G01B_BEFORE_CONSTRUCTION",
            "partition_score": score,
            "partition": assigned_partition,
            "event_id": event_id,
            "fact_bundle_identity": manifest.get("fact_atom_bundle_identity"),
            "state_identity": manifest.get("state_identity"),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "source_ids": source_ids,
            "authority_ids": authority_ids,
            "articles": articles,
            "span_checks": span_results,
            "accepted_atom_count": len(atoms),
            "atom_kinds": sorted({atom.get("kind") for atom in atoms if atom.get("kind")}),
            "syndication_or_same_event": {
                "database_event_ids": sorted({a["database_event_id"] for a in articles if a.get("database_event_id")}),
                "multiple_articles": len(article_ids) > 1,
                "multiple_authorities": len(authority_ids) > 1,
            },
            "admission": {
                "owner_final_fact_bundle": manifest.get("lifecycle") == "fact_atoms_finalized"
                or manifest.get("accepted_atoms", 0) > 0,
                "exact_spans_match_current_store": bool(span_results) and all(s["exact_match"] for s in span_results),
                "capture_time_present": bool(articles) and all(a.get("discovered_at") for a in articles),
                "source_version_present": bool(articles) and all(a.get("published_at") for a in articles),
                "permitted_use_recorded": False,
                "sensitive_protected_target_review": "NOT_RECORDED_FOR_BATCH2_V2",
                "git_object_bound": False,
                "status": "PROVISIONAL_DISCOVERY_ONLY_G01A_GAPS",
            },
            "contamination": {
                "prior_voice_fact_review_exposure": True,
                "prior_mechanic_packet_exists_in_lineage": bool(manifest.get("mechanic_packet_identity") or manifest.get("mechanic_packet_sha256")),
                "batch2_constructor_exposure": False,
                "batch2_model_exposure": False,
                "eligible_for_blind_evaluation": False,
                "blind_holdout_invalidated_by_discovery_process": event_id in INVALIDATED_BLIND_EVENT_IDS,
                "status": "BLIND_HOLDOUT_PERMANENTLY_INVALIDATED" if event_id in INVALIDATED_BLIND_EVENT_IDS else "KNOWN_PRIOR_GOVERNANCE_EXPOSURE_NOT_BLIND"
            },
        }
        if is_blind:
            content["opaque_holdout"] = True
            content["admission"]["status"] = "REJECTED_BLIND_HOLDOUT_INVALIDATED"
            content.pop("source_ids", None)
            content.pop("span_checks", None)
            content.pop("atom_kinds", None)
        families.append(content)

    output = {
        "schema_name": "pastila-humor-mechanics-batch2-v2-source-discovery-audit-output",
        "schema_version": "1.0.0",
        "plan_commit": "c756135fa9b822dd945728a2df05f26f3b44fa63",
        "plan_identity": PLAN_IDENTITY,
        "database_sha256": database_sha256,
        "families": families,
        "execution": {
            "database_mode": "READ_ONLY",
            "humor_candidate_files_read": False,
            "construction_packets_created": False,
            "candidate_surfaces_created": False,
            "model_calls": 0,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
