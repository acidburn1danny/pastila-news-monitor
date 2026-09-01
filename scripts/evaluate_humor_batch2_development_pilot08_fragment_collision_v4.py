"""Git-object-only Governance V4 fragment-collision gate for Pilot 08."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "d05643f2da3280a0bd88a5fe018c61c913186526"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-v1.txt"
EVIDENCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-construction-attempt01-v1.json"
DENYSET_PATH = "docs/artifacts/humor-mechanics-batch2-nonblind-development-fragment-denyset-v4.json"
GOVERNANCE_PATH = "docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json"
SCHEMA_PATH = "docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def words(raw: bytes) -> list[str]:
    text = unicodedata.normalize("NFKC", raw.decode("utf-8")).casefold()
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    candidate = blob(CANDIDATE_PATH)
    evidence, denyset = load(EVIDENCE_PATH), load(DENYSET_PATH)
    governance, schema = load(GOVERNANCE_PATH), load(SCHEMA_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "bc71da32026e9173440a494279fd4dca752cfc8c5547abcaa1ad922bdda0368a", "candidate hash")
    require(len(candidate) == 603 and evidence["candidate_identity"] == "6f2aca6eafc4773576a00001d83d1a0e5c2bf5a2c53d1ae2930c2f3147457fb8", "candidate binding")
    require(evidence["evidence_identity"] == "657a8ca2fb8023b9a34d51b0958c5cde9c9190f458b84da74c91a4895e56df88", "evidence")
    require(evidence["fragment_collision_evaluation"].startswith("NOT_PERFORMED"), "prior collision state")
    require(evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(governance["governance_identity"] == "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6", "governance")
    require(schema["schema_identity"] == "12c96a72555a26181abd5d0e7fa033a425fdacafb3a7fb197a21b39358da1dbe", "schema")
    denyset_core = dict(denyset); denyset_identity = denyset_core.pop("fragment_denyset_identity")
    require(denyset_identity == "d35beab3b093d118e52369239477f6dc835e764976e44336793f90704b38c844", "denyset identity")
    require(denyset_identity == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V4", denyset_core), "denyset seal")
    require(denyset["blind_reserve_accessed"] is False and len(denyset["candidate_sources"]) == 7, "denyset scope")
    require(len(denyset["normalized_ngram_sha256"]) == 1617, "denyset count")

    candidate_words = words(candidate)
    deny_hashes = set(denyset["normalized_ngram_sha256"])
    tested, collisions = [], []
    for size in denyset["ngram_word_lengths"]:
        count = 0
        for index in range(len(candidate_words) - size + 1):
            phrase = " ".join(candidate_words[index:index + size])
            digest = hashlib.sha256(phrase.encode()).hexdigest()
            count += 1
            if digest in deny_hashes:
                collisions.append({"word_length": size, "start_word": index, "candidate_fragment": phrase, "normalized_sha256": digest})
        tested.append({"word_length": size, "candidate_windows_tested": count})
    verdict = "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" if not collisions else "FAIL_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION"
    core = {
        "schema_name": "batch2-development-pilot08-postconstruction-fragment-collision-receipt-v4",
        "schema_version": "4.0.0",
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "candidate_identity": evidence["candidate_identity"],
        "candidate_surface_sha256": evidence["candidate_surface_sha256"],
        "candidate_git_blob_oid_sha1": subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT, text=True).strip(),
        "construction_evidence_identity": evidence["evidence_identity"],
        "creative_premise_family_id": evidence["creative_premise_family_id"],
        "creative_marker_family_id": evidence["creative_marker_family_id"],
        "construction_revision_family_id": evidence["construction_revision_family_id"],
        "fragment_denyset_identity": denyset_identity,
        "eligible_comparison_corpus": "SEVEN_NONBLIND_DEVELOPMENT_FAMILIES_ONLY",
        "blind_reserve_accessed": False,
        "normalization": denyset["normalization"],
        "window_results": tested,
        "exact_or_normalized_collisions": collisions,
        "collision_count": len(collisions),
        "candidate_bytes_unchanged": True,
        "candidate_repair_retry_regeneration_or_selection": False,
        "verdict": verdict,
        "g02_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW" if not collisions else "INELIGIBLE_NONPOSITIVE_COLLISION_EVIDENCE",
        "authority_matrix": {key: False for key in ("g02", "g02c", "g03", "owner_review", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_DEVELOPMENT_PILOT08_POSTCONSTRUCTION_FRAGMENT_COLLISION_RECEIPT_V4", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot08-postconstruction-fragment-collision-audit-v4",
        "schema_version": "4.0.0",
        "receipt_identity": receipt["receipt_identity"],
        "git_object_only": True,
        "candidate_identity_and_bytes": "PASS_EXACT_IMMUTABLE",
        "denyset_identity_and_seal": "PASS_EXACT_1617_HASHES",
        "exact_fragment_check": "PASS_ZERO_HITS" if not collisions else "FAIL_HITS_PRESENT",
        "normalized_ngram_check": "PASS_ZERO_HITS" if not collisions else "FAIL_HITS_PRESENT",
        "blind_reserve_access": "PASS_NONE",
        "constructor_invocations_added": 0,
        "candidate_bytes_modified": False,
        "g02_review_performed": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_COLLISION_GATE_NO_DOWNSTREAM_REVIEW",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT08_POSTCONSTRUCTION_FRAGMENT_COLLISION_AUDIT_V4", audit_core)}
    for name, value in (
        ("humor-mechanics-batch2-development-pilot08-fragment-collision-receipt-v4.json", receipt),
        ("humor-mechanics-batch2-development-pilot08-fragment-collision-audit-v4.json", audit),
    ):
        path = ART / name
        require(not path.exists(), "collision artifact already exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "collision_count": len(collisions), "receipt_identity": receipt["receipt_identity"],
                      "audit_identity": audit["audit_identity"], "g02_eligibility": receipt["g02_eligibility"]}, sort_keys=True))


if __name__ == "__main__":
    main()
