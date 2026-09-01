"""Git-object-only Governance V5.2 fragment-collision gate for Pilot 10."""

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
COMMIT = "d7d469ad3aaac777da506cafbf5ebd754890d76f"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-v1.txt"
EVIDENCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-construction-attempt01-v1.json"
DENYSET_PATH = "docs/artifacts/humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-2.json"
GOVERNANCE_PATH = "docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json"
SCHEMA_PATH = "docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json"


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
    require(hashlib.sha256(candidate).hexdigest() == "013c70e3c15833e789592915f5f31b62eeaed5c1148ff6b6f78607cb0c907464", "candidate hash")
    require(len(candidate) == 771 and evidence["candidate_identity"] == "0f17fc88debe3ba4d91740cd7541a457aa7c63fdab86abd03e9944e6e85a8f89", "candidate binding")
    require(evidence["evidence_identity"] == "f74f47e30f75b48a35deaa395d3e3de17c1c7301bacd19afbdc8e334d066f8ba", "evidence")
    require(evidence["fragment_collision_evaluation"].startswith("NOT_PERFORMED"), "prior collision state")
    require(evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1,
                                     "provider_invocations": 1, "emitter_invocations": 1}, "attempt")
    require(evidence["pre_emission_conformance"]["verdict"] == "PASS_PRE_EMISSION_REALIZATION_CONFORMANCE", "conformance")
    require(governance["governance_identity"] == "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6", "governance")
    require(schema["schema_identity"] == "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b", "schema")
    denyset_core = dict(denyset)
    denyset_identity = denyset_core.pop("fragment_denyset_identity")
    require(denyset_identity == "2cb28681d03998a0f0ae958639817aa96933648a215222f05b802c2e822efa05", "denyset identity")
    require(denyset_identity == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_2", denyset_core), "denyset seal")
    require(denyset["blind_reserve_accessed"] is False and len(denyset["candidate_sources"]) == 9, "denyset scope")
    require(len(denyset["normalized_ngram_sha256"]) == 2135, "denyset count")

    candidate_words = words(candidate)
    deny_hashes = set(denyset["normalized_ngram_sha256"])
    tested: list[dict[str, int]] = []
    collisions: list[dict[str, Any]] = []
    for size in denyset["ngram_word_lengths"]:
        count = 0
        for index in range(len(candidate_words) - size + 1):
            phrase = " ".join(candidate_words[index:index + size])
            digest = hashlib.sha256(phrase.encode()).hexdigest()
            count += 1
            if digest in deny_hashes:
                collisions.append({"word_length": size, "start_word": index,
                                   "candidate_fragment": phrase, "normalized_sha256": digest})
        tested.append({"word_length": size, "candidate_windows_tested": count})
    verdict = "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" if not collisions else "FAIL_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION"
    core = {
        "schema_name": "batch2-development-pilot10-postconstruction-fragment-collision-receipt-v5-2",
        "schema_version": "5.2.0",
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "candidate_identity": evidence["candidate_identity"],
        "candidate_surface_sha256": evidence["candidate_surface_sha256"],
        "candidate_surface_byte_length": len(candidate),
        "candidate_git_blob_oid_sha1": subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT, text=True).strip(),
        "construction_evidence_identity": evidence["evidence_identity"],
        "creative_premise_family_id": evidence["creative_premise_family_id"],
        "creative_marker_family_id": evidence["creative_marker_family_id"],
        "fragment_denyset_identity": denyset_identity,
        "eligible_comparison_corpus": "NINE_NONBLIND_DEVELOPMENT_FAMILIES_ONLY",
        "denyset_hash_count": len(denyset["normalized_ngram_sha256"]),
        "blind_reserve_accessed": False,
        "normalization": denyset["normalization"],
        "window_results": tested,
        "exact_or_normalized_collisions": collisions,
        "collision_count": len(collisions),
        "candidate_bytes_unchanged": True,
        "candidate_repair_retry_regeneration_or_selection": False,
        "verdict": verdict,
        "g02_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW" if not collisions else "INELIGIBLE_NONPOSITIVE_COLLISION_EVIDENCE",
        "authority_matrix": {key: False for key in ("g02", "g02c", "g03", "romanian_naturalness", "voice",
                              "owner_review", "g04b_pool_certification", "model_exposure", "training",
                              "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_DEVELOPMENT_PILOT10_POSTCONSTRUCTION_FRAGMENT_COLLISION_RECEIPT_V5_2", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot10-postconstruction-fragment-collision-audit-v5-2",
        "schema_version": "5.2.0",
        "receipt_identity": receipt["receipt_identity"],
        "git_object_only": True,
        "candidate_identity_and_bytes": "PASS_EXACT_IMMUTABLE",
        "denyset_identity_and_seal": "PASS_EXACT_2135_HASHES",
        "exact_fragment_check": "PASS_ZERO_HITS" if not collisions else "FAIL_HITS_PRESENT",
        "normalized_ngram_check": "PASS_ZERO_HITS" if not collisions else "FAIL_HITS_PRESENT",
        "blind_reserve_access": "PASS_NONE",
        "constructor_provider_emitter_invocations_added": "0/0/0",
        "candidate_bytes_modified": False,
        "g02_review_performed": False,
        "deterministic_blockers": [] if not collisions else ["CROSS_PILOT_FRAGMENT_COLLISION"],
        "verdict": "PASS_SOURCE_ONLY_COLLISION_GATE_NO_DOWNSTREAM_REVIEW",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT10_POSTCONSTRUCTION_FRAGMENT_COLLISION_AUDIT_V5_2", audit_core)}
    for name, value in (
        ("humor-mechanics-batch2-development-pilot10-fragment-collision-receipt-v5-2.json", receipt),
        ("humor-mechanics-batch2-development-pilot10-fragment-collision-audit-v5-2.json", audit),
    ):
        path = ART / name
        require(not path.exists(), "collision artifact already exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "collision_count": len(collisions), "receipt_identity": receipt["receipt_identity"],
                      "audit_identity": audit["audit_identity"], "g02_eligibility": receipt["g02_eligibility"]}, sort_keys=True))


if __name__ == "__main__":
    main()
