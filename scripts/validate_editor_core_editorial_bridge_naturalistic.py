"""Fail-closed validator for a future, separately frozen naturalistic evaluation bundle."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from audit_editor_core_editorial_mechanics_bridge import ART, OPERATORS, PREFIX, canonical, request, sha, shingles, similarity


def load_rows(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("truncated naturalistic JSONL")
    result = [json.loads(line) for line in raw.splitlines()]
    if any(json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() != line
           for row, line in zip(result, raw.splitlines())):
        raise ValueError("noncanonical naturalistic JSONL")
    return result


def validate(bundle: Path, artifacts: Path = ART) -> dict:
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("naturalistic bundle root")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    identity = manifest.pop("manifest_identity", None)
    if identity != sha(canonical(manifest)):
        raise ValueError("naturalistic manifest identity")
    if (manifest.get("schema"), manifest.get("schema_version"), manifest.get("case_count"),
        manifest.get("training_use"), manifest.get("collected_before_ablation")) != \
       ("editor-core-editorial-bridge-naturalistic-bundle", 1, 96, False, True):
        raise ValueError("naturalistic manifest contract")
    request_path, key_path = bundle / "requests.jsonl", bundle / "answer-key.jsonl"
    if sha(request_path.read_bytes()) != manifest.get("requests_sha256") or sha(key_path.read_bytes()) != manifest.get("answer_key_sha256"):
        raise ValueError("naturalistic requests/key blob")
    requests, keys = load_rows(request_path), load_rows(key_path)
    if len(requests) != len(keys) or len(requests) != 96:
        raise ValueError("naturalistic case count")
    if Counter(row["operator"] for row in requests) != {op: 12 for op in OPERATORS}:
        raise ValueError("naturalistic operator quota")
    if [row["case_id"] for row in requests] != [row["case_id"] for row in keys]:
        raise ValueError("naturalistic key order")
    ids, families, source_hashes = set(), set(), set()
    old_rows = []
    for label in ("train-mechanics", "development-requests", "holdout-requests"):
        old_rows += load_rows(artifacts / f"{PREFIX}-{label}.jsonl")
    for path in sorted(artifacts.glob("*.jsonl")):
        if path.name.startswith(PREFIX):
            continue
        for raw in path.read_bytes().splitlines():
            try:
                historical = json.loads(raw)
                if isinstance(historical.get("messages"), list) and len(historical["messages"]) >= 2 and "\nINPUT=" in historical["messages"][1].get("content", ""):
                    old_rows.append(historical)
            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
    old_ids = {row["example_id"] for row in old_rows}
    old_shingles = [shingles(" ".join([request(row)["request"], *(s["text"] for s in request(row)["authority_spans"])]))
                    for row in old_rows]
    maximum = 0.0
    for row, key in zip(requests, keys):
        if set(row) != {"case_id", "operator", "source_family", "source_document_sha256",
                        "source_provenance", "request", "authority_spans", "request_identity"}:
            raise ValueError("naturalistic request schema")
        if set(key) != {"case_id", "request_identity", "supported_claims", "required_qualifications",
                        "disallowed_inferences", "editorial_operation", "source_span_bindings"}:
            raise ValueError("naturalistic answer-key schema")
        case_id = row["case_id"]
        family = row["source_family"]
        document_sha = row["source_document_sha256"]
        if case_id in ids or case_id in old_ids or family in families or document_sha in source_hashes:
            raise ValueError("naturalistic case/source overlap")
        ids.add(case_id); families.add(family); source_hashes.add(document_sha)
        if not row["source_provenance"] or not row["request"] or not row["authority_spans"]:
            raise ValueError("naturalistic provenance/request")
        document = bundle / "sources" / (document_sha + ".txt")
        if document.is_symlink() or not document.is_file() or sha(document.read_bytes()) != document_sha:
            raise ValueError("naturalistic source document hash")
        source_text = document.read_text(encoding="utf-8")
        if any(span["text"] not in source_text for span in row["authority_spans"]):
            raise ValueError("naturalistic span not present in source")
        core = {k: v for k, v in row.items() if k != "request_identity"}
        if row["request_identity"] != "sha256:" + sha(canonical(core)) or key["request_identity"] != row["request_identity"]:
            raise ValueError("naturalistic case/key identity")
        if not key["supported_claims"] or not key["source_span_bindings"] or key["editorial_operation"] != row["operator"]:
            raise ValueError("naturalistic scoring key")
        current = shingles(" ".join([row["request"], *(s["text"] for s in row["authority_spans"])]))
        maximum = max(maximum, *(similarity(current, old) for old in old_shingles))
    if maximum >= 0.72:
        raise ValueError("naturalistic lexical contamination")
    if set(manifest.get("source_document_sha256", [])) != source_hashes or len(manifest["source_document_sha256"]) != 96:
        raise ValueError("naturalistic source closure")
    # Hashes and lexical checks cannot establish that a source was independently
    # captured from a real document. In particular, the fixture bundle below
    # satisfies every structural check. Do not expose a terminal PASS here.
    return {"verdict": "PASS_STRUCTURAL_ONLY_PROVENANCE_UNVERIFIED", "blockers": 0,
            "naturalistic_provenance_verified": False,
            "eligible_for_ablation_gate": False, "manifest_identity": identity, "cases": 96,
            "operator_cases_each": 12, "maximum_bridge_jaccard_5gram": round(maximum, 4),
            "answer_key_outside_inference": True, "training_use": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.bundle), sort_keys=True))
